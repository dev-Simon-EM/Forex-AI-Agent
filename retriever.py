"""Knowledge retriever using LangChain + Chroma + HuggingFace embeddings.

Functions:
- load_knowledge(): loads text notes and builds/loads a Chroma vectorstore
- query_knowledge(question, k=4): returns top-k similar passages as concatenated context

Uses sentence-transformers for embeddings (no API key required).
"""

import os
from typing import List, Tuple

from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_text_splitters import CharacterTextSplitter


DB_DIR = os.path.join(os.path.dirname(__file__), "chroma_db")
COLLECTION_NAME = "smc_notes"


def _ensure_db_dir():
    os.makedirs(DB_DIR, exist_ok=True)


def load_knowledge(smc_path: str = None):
    """Load SMC notes and return a Chroma vectorstore.

    If the DB already exists, it will be loaded. Otherwise, it will be created from
    the `data/smc_notes.txt` file.
    """
    _ensure_db_dir()
    if smc_path is None:
        smc_path = os.path.join(os.path.dirname(__file__), "data", "smc_notes.txt")

    if not os.path.isfile(smc_path):
        raise FileNotFoundError(f"Knowledge file not found: {smc_path}")

    with open(smc_path, "r", encoding="utf-8") as f:
        raw = f.read().strip()

    if not raw:
        raise ValueError("SMC notes file is empty")

    # Create embeddings object using HuggingFace (no API key needed)
    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    )

    # If a persisted collection exists, try to load it
    try:
        db = Chroma(persist_directory=DB_DIR, collection_name=COLLECTION_NAME, embedding_function=embeddings)
        # quick check: if empty, fall back to creating from texts
        if db._collection.count() if hasattr(db, "_collection") else 0:
            return db
    except Exception:
        db = None

    # Split text into chunks and create vectorstore
    splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=0)
    texts = splitter.split_text(raw)

    db = Chroma.from_texts(texts, embeddings, collection_name=COLLECTION_NAME, persist_directory=DB_DIR)
    db.persist()
    return db


def query_knowledge(question: str, k: int = 4) -> str:
    """Return concatenated context string for the question."""
    db = load_knowledge()
    results = db.similarity_search(question, k=k)
    passages = [doc.page_content for doc in results]
    context = "\n\n".join(passages)
    return context
 