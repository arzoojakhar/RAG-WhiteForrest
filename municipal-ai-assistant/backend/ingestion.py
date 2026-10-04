"""
Document ingestion pipeline.
Parses PDFs, Word docs and Excel files, chunks text, stores in ChromaDB
with rich metadata: source_file, page_number, chunk_index, char_start, char_end.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Literal

import chromadb
import pdfplumber
import pypdf
from chromadb.utils.embedding_functions import OllamaEmbeddingFunction
from docx import Document as DocxDocument
from langchain_text_splitters import RecursiveCharacterTextSplitter
from openpyxl import load_workbook
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

import config

DocType = Literal["knowledge_base", "additional_documents"]

# ── ChromaDB client (shared singleton) ───────────────────────────────────────
_chroma_client: chromadb.PersistentClient | None = None
_collections: dict[str, chromadb.Collection] = {}


def get_chroma_client() -> chromadb.PersistentClient:
    global _chroma_client
    if _chroma_client is None:
        _chroma_client = chromadb.PersistentClient(path=str(config.CHROMA_DIR))
    return _chroma_client


def get_collection(name: str) -> chromadb.Collection:
    if name not in _collections:
        client = get_chroma_client()
        # embed_fn = OllamaEmbeddingFunction(
        #     model_name=config.EMBEDDING_MODEL,
        #     url=f"{config.OLLAMA_BASE_URL}/api/embeddings",
        # )

        embed_fn = SentenceTransformerEmbeddingFunction(
            model_name="sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
        )
        _collections[name] = client.get_or_create_collection(
            name=name,
            embedding_function=embed_fn,
            metadata={"hnsw:space": "cosine"},
        )
    return _collections[name]


# ── Text splitter ─────────────────────────────────────────────────────────────
_splitter = RecursiveCharacterTextSplitter(
    chunk_size=config.CHUNK_SIZE,
    chunk_overlap=config.CHUNK_OVERLAP,
    separators=["\n\n", "\n", ". ", " ", ""],
)


# ── Parsers ───────────────────────────────────────────────────────────────────

def _parse_pdf(path: Path) -> list[dict]:
    """Return list of {page, text} dicts from a PDF."""
    pages = []
    try:
        with pdfplumber.open(path) as pdf:
            for i, page in enumerate(pdf.pages, start=1):
                text = page.extract_text() or ""
                if text.strip():
                    pages.append({"page": i, "text": text})
    except Exception:
        # Fallback to pypdf
        reader = pypdf.PdfReader(str(path))
        for i, page in enumerate(reader.pages, start=1):
            text = page.extract_text() or ""
            if text.strip():
                pages.append({"page": i, "text": text})
    return pages


def _parse_docx(path: Path) -> list[dict]:
    doc = DocxDocument(str(path))
    full_text = "\n".join(p.text for p in doc.paragraphs if p.text.strip())
    return [{"page": 1, "text": full_text}]


def _parse_xlsx(path: Path) -> list[dict]:
    wb = load_workbook(str(path), read_only=True, data_only=True)
    parts = []
    for sheet_name in wb.sheetnames:
        ws = wb[sheet_name]
        rows = []
        for row in ws.iter_rows(values_only=True):
            cells = [str(c) for c in row if c is not None]
            if cells:
                rows.append(" | ".join(cells))
        if rows:
            parts.append({"page": sheet_name, "text": "\n".join(rows)})
    return parts


def _parse_file(path: Path) -> list[dict]:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return _parse_pdf(path)
    elif suffix in {".docx", ".doc"}:
        return _parse_docx(path)
    elif suffix in {".xlsx", ".xls"}:
        return _parse_xlsx(path)
    return []


# ── Ingestion entry-point ─────────────────────────────────────────────────────

def _make_chunk_id(source: str, page: str | int, chunk_idx: int) -> str:
    raw = f"{source}::{page}::{chunk_idx}"
    return hashlib.md5(raw.encode()).hexdigest()


def ingest_file(path: Path, doc_type: DocType) -> dict:
    """
    Parse `path`, chunk text, embed and upsert into ChromaDB.
    Returns a summary dict.
    """
    collection_name = (
        config.COLLECTION_KB if doc_type == "knowledge_base" else config.COLLECTION_EXTRA
    )
    collection = get_collection(collection_name)

    pages = _parse_file(path)
    if not pages:
        return {"file": path.name, "status": "no_text_extracted", "chunks": 0}

    all_texts: list[str] = []
    all_ids:   list[str] = []
    all_metas: list[dict] = []

    for page_data in pages:
        page_label = str(page_data["page"])
        page_text  = page_data["text"]
        chunks     = _splitter.split_text(page_text)

        for chunk_idx, chunk_text in enumerate(chunks):
            chunk_id = _make_chunk_id(path.name, page_label, chunk_idx)
            # Calculate approximate character positions within the page
            char_start = page_text.find(chunk_text[:50])
            char_end   = char_start + len(chunk_text) if char_start >= 0 else -1

            all_texts.append(chunk_text)
            all_ids.append(chunk_id)
            all_metas.append({
                "source_file":  path.name,
                "source_path":  str(path),
                "page":         page_label,
                "chunk_index":  chunk_idx,
                "char_start":   char_start,
                "char_end":     char_end,
                "doc_type":     doc_type,
            })

    # Upsert in batches of 100
    batch_size = 100
    for i in range(0, len(all_texts), batch_size):
        collection.upsert(
            documents=all_texts[i : i + batch_size],
            ids=all_ids[i : i + batch_size],
            metadatas=all_metas[i : i + batch_size],
        )

    return {
        "file":       path.name,
        "status":     "ok",
        "chunks":     len(all_texts),
        "pages":      len(pages),
        "collection": collection_name,
    }


def ingest_directory(directory: Path, doc_type: DocType) -> list[dict]:
    """Ingest all supported files in a directory."""
    results = []
    for path in directory.iterdir():
        if path.suffix.lower() in {".pdf", ".docx", ".doc", ".xlsx", ".xls"}:
            results.append(ingest_file(path, doc_type))
    return results


def delete_file_from_index(filename: str, doc_type: DocType) -> int:
    """Remove all chunks belonging to `filename` from the collection."""
    collection_name = (
        config.COLLECTION_KB if doc_type == "knowledge_base" else config.COLLECTION_EXTRA
    )
    collection = get_collection(collection_name)
    results = collection.get(where={"source_file": filename})
    ids = results.get("ids", [])
    if ids:
        collection.delete(ids=ids)
    return len(ids)


def list_ingested_files(doc_type: DocType) -> list[dict]:
    """Return unique files currently in the collection with chunk counts."""
    collection_name = (
        config.COLLECTION_KB if doc_type == "knowledge_base" else config.COLLECTION_EXTRA
    )
    collection = get_collection(collection_name)
    results = collection.get(include=["metadatas"])
    metas = results.get("metadatas", []) or []

    files: dict[str, dict] = {}
    for m in metas:
        name = m.get("source_file", "unknown")
        if name not in files:
            files[name] = {"filename": name, "doc_type": doc_type, "chunks": 0}
        files[name]["chunks"] += 1

    return list(files.values())
