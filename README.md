# AI Resume Analyzer

Course-project implementation based on the supplied SRS.

## Stack
- Backend: Python + FastAPI
- Database: SQLite
- Frontend: HTML + CSS + Vanilla JavaScript
- Resume files: PDF / DOCX
- AI: configurable Gemini REST API
- RAG: local knowledge base + TF-IDF retrieval

## Run
1. Open this folder in VS Code.
2. `python -m venv venv`
3. Windows: `venv\Scripts\activate`
4. `pip install -r requirements.txt`
5. Copy `.env.example` to `.env`.
6. Put your Gemini API key in `.env`.
7. Run: `uvicorn app.main:app --reload`
8. Open: `http://127.0.0.1:8000`
9. API documentation: `http://127.0.0.1:8000/docs`

If Gemini is unavailable, extraction, skill detection, job matching and RAG retrieval
still work and the app returns a fallback instead of crashing.
