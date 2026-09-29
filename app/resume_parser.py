from pathlib import Path
from pypdf import PdfReader
from docx import Document

def extract_resume_text(path):
    ext = Path(path).suffix.lower()
    if ext == ".pdf":
        reader = PdfReader(path)
        return "\n".join(page.extract_text() or "" for page in reader.pages).strip()
    if ext == ".docx":
        doc = Document(path)
        return "\n".join(p.text for p in doc.paragraphs).strip()
    raise ValueError("Only PDF and DOCX files are supported.")
