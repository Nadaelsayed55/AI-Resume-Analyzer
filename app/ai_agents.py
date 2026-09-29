import os
import json
import re
import httpx

from .rag import retrieve


SKILLS = [
    "python", "java", "javascript", "typescript", "c++", "sql",
    "html", "css", "fastapi", "django", "flask", "react", "node.js",
    "git", "docker", "machine learning", "deep learning", "nlp",
    "pandas", "numpy", "scikit-learn", "tensorflow", "pytorch",
    "communication", "leadership", "teamwork", "problem solving",
    "time management"
]

SOFT = {
    "communication",
    "leadership",
    "teamwork",
    "problem solving",
    "time management"
}


# =========================================================
# Detect Skills
# =========================================================

def detect_skills(text):
    low = text.lower()
    return sorted({
        skill for skill in SKILLS
        if skill in low
    })


# =========================================================
# Extract Education
# =========================================================

def extract_education(text):
    education = []

    match = re.search(
        r"(?:education|academic background|academic qualifications)"
        r"(.*?)(?=\n(?:experience|work experience|technical skills|skills|projects|certifications|achievements)\b|\Z)",
        text,
        re.IGNORECASE | re.DOTALL
    )

    if not match:
        return education

    section = match.group(1).strip()

    lines = [
        line.strip()
        for line in section.splitlines()
        if line.strip()
    ]

    current = {}

    for line in lines:
        low = line.lower()

        if any(word in low for word in [
            "bachelor",
            "master",
            "phd",
            "degree",
            "b.sc",
            "bsc",
            "m.sc",
            "msc"
        ]):
            if current:
                education.append(current)

            current = {
                "degree": line
            }

        elif any(word in low for word in [
            "university",
            "college",
            "institute"
        ]):
            current["institution"] = line

        elif "gpa" in low:
            current["gpa"] = line

        elif re.search(
            r"\b20\d{2}\s*[-–]\s*(?:20\d{2}|present)\b",
            line,
            re.IGNORECASE
        ):
            current["years"] = line

    if current:
        education.append(current)

    return education


# =========================================================
# Extract Experience
# =========================================================

def extract_experience(text):
    experience = []

    match = re.search(
        r"(?:experience|work experience|professional experience)"
        r"(.*?)(?=\n(?:education|skills|technical skills|projects|certifications|achievements)\b|\Z)",
        text,
        re.IGNORECASE | re.DOTALL
    )

    if not match:
        return experience

    section = match.group(1).strip()

    lines = [
        line.strip()
        for line in section.splitlines()
        if line.strip()
    ]

    current = {}

    for line in lines:

        if re.search(
            r"\b(developer|engineer|analyst|intern|scientist|manager|specialist|trainee|data analyst|machine learning)\b",
            line,
            re.IGNORECASE
        ):
            if current:
                experience.append(current)

            current = {
                "position": line
            }

        elif re.search(
            r"\b20\d{2}\s*[-–]\s*(?:20\d{2}|present)\b",
            line,
            re.IGNORECASE
        ):
            current["years"] = line

        elif current:
            current.setdefault("details", []).append(line)

    if current:
        experience.append(current)

    return experience


# =========================================================
# Detect Weaknesses
# =========================================================

def detect_weaknesses(text, skills):

    weaknesses = []

    low = text.lower()

    if "sql" not in skills:
        weaknesses.append(
            "SQL is not clearly demonstrated in the resume."
        )

    if "git" not in skills:
        weaknesses.append(
            "Git is not clearly demonstrated in the resume."
        )

    if "docker" not in skills:
        weaknesses.append(
            "Docker is not clearly demonstrated in the resume."
        )

    if "communication" not in skills:
        weaknesses.append(
            "Communication skills are not explicitly demonstrated."
        )

    if "projects" not in low:
        weaknesses.append(
            "Projects are not clearly identified in the resume."
        )

    return weaknesses


# =========================================================
# Heuristic Analysis
# =========================================================

def heuristic_analysis(text):

    skills = detect_skills(text)

    technical_skills = [
        skill for skill in skills
        if skill not in SOFT
    ]

    soft_skills = [
        skill for skill in skills
        if skill in SOFT
    ]

    education = extract_education(text)

    experience = extract_experience(text)

    weaknesses = detect_weaknesses(
        text,
        skills
    )

    return {
        "summary": (
            text[:1200]
            if text
            else "No resume text was extracted."
        ),

        "technical_skills": technical_skills,

        "soft_skills": soft_skills,

        "education": education,

        "experience": experience,

        "strengths": technical_skills[:8],

        "weaknesses": weaknesses
    }


# =========================================================
# Gemini API
# =========================================================

async def call_gemini(prompt):

    key = os.getenv("GEMINI_API_KEY")

    model = os.getenv(
        "GEMINI_MODEL",
        "gemini-2.5-flash"
    )

    print("\n==============================")
    print("GEMINI DEBUG")
    print("==============================")

    print("Gemini API Key exists:",
          bool(key))

    print("Gemini Model:",
          model)

    if not key:
        print("ERROR: GEMINI_API_KEY is missing.")

        return None

    url = (
        "https://generativelanguage.googleapis.com/"
        f"v1beta/models/{model}:generateContent"
    )

    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "text": prompt
                    }
                ]
            }
        ]
    }

    headers = {
        "x-goog-api-key": key,
        "Content-Type": "application/json"
    }

    try:

        async with httpx.AsyncClient(
            timeout=180
        ) as client:

            response = await client.post(
                url,
                headers=headers,
                json=payload
            )

        print("Gemini HTTP Status:",
              response.status_code)

        print("Gemini Response:")
        print(response.text)

        response.raise_for_status()

        data = response.json()

        try:

            result = (
                data["candidates"][0]
                ["content"]["parts"][0]["text"]
            )

            print("==============================")
            print("GEMINI SUCCESS")
            print("==============================")

            return result

        except (KeyError, IndexError):

            print("==============================")
            print("GEMINI RESPONSE FORMAT ERROR")
            print("==============================")

            print(data)

            return None

    except Exception as e:

        print("==============================")
        print("GEMINI REQUEST ERROR")
        print("==============================")

        print("Error Type:",
              type(e).__name__)

        print("Error:",
              str(e))

        return None


# =========================================================
# Resume Analyzer Agent
# =========================================================

async def resume_analyzer_agent(text):

    base = heuristic_analysis(text)

    context = retrieve(
        text[:4000],
        3
    )

    context_text = "\n\n".join(
        item["text"]
        for item in context
    )

    prompt = f"""
You are the Resume Analyzer Agent.

Return ONLY valid JSON.

The JSON must contain these keys:

summary
technical_skills
soft_skills
education
experience
strengths
weaknesses

Rules:

1. Extract education from the resume.
2. Extract work experience, internships and training from the resume.
3. Identify technical skills.
4. Identify soft skills.
5. Identify strengths based only on evidence in the resume.
6. Identify areas for improvement based only on missing
   or weakly demonstrated information.
7. Do not invent facts.
8. Use empty lists when information is genuinely absent.

RAG context:

{context_text}

Resume:

{text[:12000]}
"""

    print("\n==============================")
    print("CALLING RESUME ANALYZER AGENT")
    print("==============================")

    try:

        raw = await call_gemini(prompt)

        print("\n===== GEMINI RAW RESPONSE =====")

        print(raw)

        if raw:

            cleaned = raw.strip()

            cleaned = re.sub(
                r"^```json\s*",
                "",
                cleaned,
                flags=re.IGNORECASE
            )

            cleaned = re.sub(
                r"\s*```$",
                "",
                cleaned
            )

            print("\n===== CLEANED RESPONSE =====")

            print(cleaned)

            result = json.loads(cleaned)

            print("\n===== JSON PARSED SUCCESSFULLY =====")

            return result

    except json.JSONDecodeError as e:

        print("\n===== JSON ERROR =====")

        print("Gemini returned something that is not valid JSON.")

        print("Error:",
              str(e))

    except Exception as e:

        print("\n===== RESUME ANALYZER ERROR =====")

        print("Error Type:",
              type(e).__name__)

        print("Error:",
              str(e))

    print("\n===== USING HEURISTIC FALLBACK =====")

    return base


# =========================================================
# Job Matching Agent
# =========================================================

async def job_matching_agent(
    resume_text,
    job
):

    resume_skills = set(
        detect_skills(resume_text)
    )

    job_skills = set(
        detect_skills(
            (job.description or "")
            + " "
            + (job.skills or "")
        )
    )

    score = (
        round(
            len(
                resume_skills & job_skills
            )
            /
            len(job_skills)
            * 100,
            2
        )
        if job_skills
        else 0
    )

    matched = sorted(
        resume_skills & job_skills
    )

    missing = sorted(
        job_skills - resume_skills
    )

    prompt = f"""
You are the Job Matching Agent.

Resume skills:

{sorted(resume_skills)}

Job title:

{job.title}

Job skills:

{sorted(job_skills)}

Matched skills:

{matched}

Missing skills:

{missing}

Give a short explanation.

Do not invent resume facts.
"""

    try:

        explanation = await call_gemini(
            prompt
        )

    except Exception as e:

        print(
            "Job Matching Gemini Error:",
            str(e)
        )

        explanation = None

    if not explanation:

        explanation = (
            f"Matched skills: "
            f"{', '.join(matched) or 'none'}. "
            f"Missing skills: "
            f"{', '.join(missing) or 'none'}."
        )

    return {
        "score": score,

        "matched_skills": matched,

        "missing_skills": missing,

        "explanation": explanation
    }


# =========================================================
# Career Advisor Agent
# =========================================================

async def career_advisor_agent(
    resume_text
):

    context = retrieve(
        resume_text[:4000],
        4
    )

    context_text = "\n\n".join(
        item["text"]
        for item in context
    )

    prompt = f"""
You are the Career Advisor Agent.

Using only the resume and retrieved knowledge,
provide:

1. Missing skills
2. Suggested certifications
3. Learning resources
4. Resume improvements
5. Two possible next career steps

Do not invent experience.

Retrieved knowledge:

{context_text}

Resume:

{resume_text[:10000]}
"""

    try:

        answer = await call_gemini(
            prompt
        )

    except Exception as e:

        print(
            "Career Advisor Gemini Error:",
            str(e)
        )

        answer = None

    if answer:

        return answer

    skills = detect_skills(
        resume_text
    )

    return (
        "Fallback advice:\n"
        "Detected skills: "
        + (
            ", ".join(skills)
            or "none"
        )
        + ".\n"
        "Review target-job requirements "
        "and build projects around "
        "missing skills."
    )