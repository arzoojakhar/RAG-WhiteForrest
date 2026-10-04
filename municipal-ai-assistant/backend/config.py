"""
Configuration for the Municipal AI Assistant.
All settings are kept local – no external API calls.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env", override=False)

# ── Paths ────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
KNOWLEDGE_BASE_DIR = DATA_DIR / "knowledge_base"
ADDITIONAL_DOCS_DIR = DATA_DIR / "additional_documents"
TEMPLATES_DIR       = DATA_DIR / "templates"
UPLOADS_DIR         = DATA_DIR / "uploads"
CHROMA_DIR          = DATA_DIR / "chroma_db"
FILLED_OUTPUT_DIR   = DATA_DIR / "filled_templates"

for _d in [KNOWLEDGE_BASE_DIR, ADDITIONAL_DOCS_DIR, TEMPLATES_DIR,
           UPLOADS_DIR, CHROMA_DIR, FILLED_OUTPUT_DIR]:
    _d.mkdir(parents=True, exist_ok=True)

# ── Ollama / LLM ─────────────────────────────────────────────────────────────
OLLAMA_BASE_URL   = os.getenv("OLLAMA_BASE_URL", "http://localhost:8080") #http://localhost:11434 
CHAT_MODEL        = os.getenv("CHAT_MODEL",       "mistral-large:123b")   #llama3:8b-instruct-q4_0       # local Mistral
EMBEDDING_MODEL   = os.getenv("EMBEDDING_MODEL",  "sentence-transformers/paraphrase-multilingual-mpnet-base-v2") # local embeddings

# ── RAG / Retrieval ───────────────────────────────────────────────────────────
CHUNK_SIZE           = 2000   # larger chunks = more context per passage
CHUNK_OVERLAP        = 200    # generous overlap so nothing is cut at boundaries
TOP_K_RETRIEVAL      = 5      # 5 chunks × 1500 chars fits well in 4096 ctx
MIN_RELEVANCE_SCORE  = 0.20   # lower threshold – let Mistral decide relevance
LLM_TEMPERATURE      = 0.1    # tiny non-zero: avoids repetition loops
LLM_NUM_PREDICT      = 2048   # max output tokens – prevents truncated answers

# ── ChromaDB collection names ─────────────────────────────────────────────────
COLLECTION_KB    = "knowledge_base"
COLLECTION_EXTRA = "additional_documents"

# ── CORS (frontend dev server) ────────────────────────────────────────────────
CORS_ORIGINS = ["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173"]
