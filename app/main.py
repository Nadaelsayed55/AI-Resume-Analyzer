import json
from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from .database import Base, engine, get_db
from .models import User, Resume, Job, Match
from .auth import hash_password, verify_password, create_token, get_user_id
from .resume_parser import extract_resume_text
from .ai_agents import resume_analyzer_agent, job_matching_agent, career_advisor_agent

load_dotenv()
Base.metadata.create_all(bind=engine)

app = FastAPI(title="AI Resume Analyzer API", version="1.0")
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"]
)

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory="app/static"), name="static")

class RegisterIn(BaseModel):
    name: str
    email: EmailStr
    password: str

class LoginIn(BaseModel):
    email: EmailStr
    password: str

class JobIn(BaseModel):
    title: str
    company: str
    description: str
    skills: str = ""
    location: str = ""

def current_user(authorization):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Login required")
    return get_user_id(authorization[7:])

@app.get("/")
def home():
    return FileResponse("app/static/index.html")

@app.post("/api/auth/register")
def register(data: RegisterIn, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == data.email).first():
        raise HTTPException(400, "Email already registered")
    if len(data.password) < 6:
        raise HTTPException(400, "Password must be at least 6 characters")
    user = User(name=data.name, email=data.email, password_hash=hash_password(data.password))
    db.add(user); db.commit(); db.refresh(user)
    return {"message": "Registered successfully", "token": create_token(user.id)}

@app.post("/api/auth/login")
def login(data: LoginIn, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email).first()
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(401, "Invalid email or password")
    return {"message": "Login successful", "token": create_token(user.id)}

@app.post("/api/auth/logout")
def logout():
    return {"message": "Delete the token from the browser."}

@app.post("/api/resumes/upload")
async def upload_resume(
    file: UploadFile = File(...),
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db)
):
    user_id = current_user(authorization)
    ext = Path(file.filename or "").suffix.lower()
    if ext not in {".pdf", ".docx"}:
        raise HTTPException(400, "Only PDF and DOCX files are allowed")
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(400, "Maximum file size is 10 MB")
    path = UPLOAD_DIR / f"{user_id}_{Path(file.filename).name}"
    path.write_bytes(content)
    try:
        text = extract_resume_text(str(path))
    except Exception as e:
        raise HTTPException(400, f"Could not read resume: {e}")
    analysis = await resume_analyzer_agent(text)
    resume = Resume(user_id=user_id, filename=file.filename,
                    extracted_text=text, analysis_json=json.dumps(analysis))
    db.add(resume); db.commit(); db.refresh(resume)
    return {"resume_id": resume.id, "filename": resume.filename, "analysis": analysis}

@app.get("/api/resumes")
def list_resumes(authorization: str | None = Header(default=None), db: Session = Depends(get_db)):
    uid = current_user(authorization)
    rows = db.query(Resume).filter(Resume.user_id == uid).order_by(Resume.id.desc()).all()
    return [{"id": r.id, "filename": r.filename, "created_at": r.created_at} for r in rows]

@app.get("/api/resumes/{resume_id}")
def get_resume(resume_id: int, authorization: str | None = Header(default=None), db: Session = Depends(get_db)):
    uid = current_user(authorization)
    r = db.query(Resume).filter(Resume.id == resume_id, Resume.user_id == uid).first()
    if not r:
        raise HTTPException(404, "Resume not found")
    return {"id": r.id, "filename": r.filename,
            "analysis": json.loads(r.analysis_json or "{}"), "text": r.extracted_text}

@app.post("/api/jobs")
def add_job(data: JobIn, authorization: str | None = Header(default=None), db: Session = Depends(get_db)):
    current_user(authorization)
    job = Job(**data.model_dump())
    db.add(job); db.commit(); db.refresh(job)
    return job_to_dict(job)

@app.get("/api/jobs")
def get_jobs(q: str = "", location: str = "", db: Session = Depends(get_db)):
    query = db.query(Job)
    if q:
        like = f"%{q}%"
        query = query.filter((Job.title.ilike(like)) | (Job.description.ilike(like)) | (Job.skills.ilike(like)))
    if location:
        query = query.filter(Job.location.ilike(f"%{location}%"))
    return [job_to_dict(j) for j in query.order_by(Job.id.desc()).all()]

@app.put("/api/jobs/{job_id}")
def edit_job(job_id: int, data: JobIn, authorization: str | None = Header(default=None), db: Session = Depends(get_db)):
    current_user(authorization)
    job = db.get(Job, job_id)
    if not job: raise HTTPException(404, "Job not found")
    for k, v in data.model_dump().items(): setattr(job, k, v)
    db.commit()
    return job_to_dict(job)

@app.delete("/api/jobs/{job_id}")
def delete_job(job_id: int, authorization: str | None = Header(default=None), db: Session = Depends(get_db)):
    current_user(authorization)
    job = db.get(Job, job_id)
    if not job: raise HTTPException(404, "Job not found")
    db.delete(job); db.commit()
    return {"message": "Job deleted"}

@app.post("/api/match/{resume_id}/{job_id}")
async def match_job(resume_id: int, job_id: int, authorization: str | None = Header(default=None),
                    db: Session = Depends(get_db)):
    uid = current_user(authorization)
    resume = db.query(Resume).filter(Resume.id == resume_id, Resume.user_id == uid).first()
    job = db.get(Job, job_id)
    if not resume or not job: raise HTTPException(404, "Resume or job not found")
    result = await job_matching_agent(resume.extracted_text, job)
    row = Match(resume_id=resume.id, job_id=job.id, score=result["score"], explanation=result["explanation"])
    db.add(row); db.commit()
    return {"job": job_to_dict(job), **result}

@app.get("/api/career-advice/{resume_id}")
async def career_advice(resume_id: int, authorization: str | None = Header(default=None),
                        db: Session = Depends(get_db)):
    uid = current_user(authorization)
    resume = db.query(Resume).filter(Resume.id == resume_id, Resume.user_id == uid).first()
    if not resume: raise HTTPException(404, "Resume not found")
    return {"advice": await career_advisor_agent(resume.extracted_text)}

def job_to_dict(j):
    return {"id": j.id, "title": j.title, "company": j.company,
            "description": j.description, "skills": j.skills, "location": j.location}
