from pathlib import Path
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

KB_DIR = Path("knowledge_base")

def load_documents():
    return [
        {"name": p.name, "text": p.read_text(encoding="utf-8")}
        for p in KB_DIR.glob("*.txt")
    ]

def retrieve(query, top_k=3):
    docs = load_documents()
    if not docs:
        return []
    corpus = [d["text"] for d in docs]
    vectorizer = TfidfVectorizer(stop_words="english")
    matrix = vectorizer.fit_transform(corpus + [query])
    scores = cosine_similarity(matrix[-1], matrix[:-1]).flatten()
    order = scores.argsort()[::-1][:top_k]
    return [
        {"name": docs[i]["name"], "text": docs[i]["text"], "score": float(scores[i])}
        for i in order
    ]
