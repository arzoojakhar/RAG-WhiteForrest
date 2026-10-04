"""
FastAPI backend for the Municipal AI Assistant.
"""
from __future__ import annotations

import shutil
import uuid
from pathlib import Path
from typing import Any, Optional

import aiofiles
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import config
import ingestion
from agent import run_agent
from rag_chain import answer_question
from template_filler import (
    TemplateField,
    apply_user_input,
    extract_fields,
    fill_fields_with_rag,
    produce_filled_file,
)

# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Municipal AI Assistant",
    description="KI-Assistent für kommunale Energiewende-Dokumente",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory session store for template fill sessions (keyed by session_id)
# In production this would be a DB or Redis
_template_sessions: dict[str, dict[str, Any]] = {}


# ── Pydantic models ───────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    question: str
    use_agent: bool = True  # use LangGraph agent (True) or simple RAG (False)


class CitationOut(BaseModel):
    source_file: str
    page: str
    excerpt: str
    relevance_score: float


class ChatResponse(BaseModel):
    answer: str
    citations: list[CitationOut]
    is_uncertain: bool
    clarification_request: Optional[str]


class FieldOut(BaseModel):
    field_id: str
    label: str
    location: str
    current_value: Optional[str]
    filled_value: Optional[str]
    citation: Optional[str]
    confidence: float
    status: str


class TemplateAnalysisResponse(BaseModel):
    session_id: str
    filename: str
    fields: list[FieldOut]


class UserInputUpdate(BaseModel):
    session_id: str
    updates: dict[str, str]  # field_id → user-provided value


class DocumentInfo(BaseModel):
    filename: str
    doc_type: str
    chunks: int


# ── Health check ──────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok", "model": config.CHAT_MODEL, "embedding": config.EMBEDDING_MODEL}


# ── Chat endpoint ─────────────────────────────────────────────────────────────

@app.post("/api/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    if not req.question.strip():
        raise HTTPException(status_code=400, detail="Frage darf nicht leer sein.")

    # Always use direct RAG for reliable, complete answers with Mistral 7B.
    # The LangGraph agent path is kept as opt-in only (use_agent=True AND agent available).
    result = answer_question(req.question)

    return ChatResponse(
        answer=result.answer,
        citations=[
            CitationOut(
                source_file=c.source_file,
                page=c.page,
                excerpt=c.excerpt,
                relevance_score=c.relevance_score,
            )
            for c in result.citations
        ],
        is_uncertain=result.is_uncertain,
        clarification_request=result.clarification_request,
    )


# ── Knowledge base document endpoints ────────────────────────────────────────

@app.get("/api/documents", response_model=list[DocumentInfo])
def list_documents():
    kb    = ingestion.list_ingested_files("knowledge_base")
    extra = ingestion.list_ingested_files("additional_documents")
    return [DocumentInfo(**d) for d in kb + extra]


@app.post("/api/documents/upload")
async def upload_document(
    file: UploadFile = File(...),
    doc_type: str = Form("knowledge_base"),
):
    if doc_type not in {"knowledge_base", "additional_documents"}:
        raise HTTPException(status_code=400, detail="Ungültiger doc_type.")

    target_dir = (
        config.KNOWLEDGE_BASE_DIR
        if doc_type == "knowledge_base"
        else config.ADDITIONAL_DOCS_DIR
    )
    dest = target_dir / file.filename

    async with aiofiles.open(dest, "wb") as f:
        content = await file.read()
        await f.write(content)

    result = ingestion.ingest_file(dest, doc_type)  # type: ignore[arg-type]
    return {"message": "Dokument hochgeladen und indiziert.", "details": result}


@app.delete("/api/documents/{doc_type}/{filename}")
def delete_document(doc_type: str, filename: str):
    if doc_type not in {"knowledge_base", "additional_documents"}:
        raise HTTPException(status_code=400, detail="Ungültiger doc_type.")

    target_dir = (
        config.KNOWLEDGE_BASE_DIR
        if doc_type == "knowledge_base"
        else config.ADDITIONAL_DOCS_DIR
    )
    file_path = target_dir / filename
    if file_path.exists():
        file_path.unlink()

    deleted = ingestion.delete_file_from_index(filename, doc_type)  # type: ignore[arg-type]
    return {"message": f"{deleted} Chunks aus dem Index entfernt.", "filename": filename}


@app.post("/api/documents/reindex")
def reindex_all():
    """Re-ingest all documents in both directories."""
    results = []
    results += ingestion.ingest_directory(config.KNOWLEDGE_BASE_DIR, "knowledge_base")
    results += ingestion.ingest_directory(config.ADDITIONAL_DOCS_DIR, "additional_documents")
    return {"message": "Neuindizierung abgeschlossen.", "results": results}


# ── Template endpoints ────────────────────────────────────────────────────────

@app.post("/api/templates/analyze", response_model=TemplateAnalysisResponse)
async def analyze_template(file: UploadFile = File(...)):
    """Upload a template, extract fields, attempt RAG fill, return field list."""
    dest = config.UPLOADS_DIR / file.filename
    async with aiofiles.open(dest, "wb") as f:
        content = await file.read()
        await f.write(content)

    fields = extract_fields(dest)
    if not fields:
        raise HTTPException(
            status_code=422,
            detail="Keine Felder im Template erkannt. Bitte prüfen Sie das Dateiformat.",
        )

    # Try filling via RAG
    filled_fields = fill_fields_with_rag(fields)

    session_id = str(uuid.uuid4())
    _template_sessions[session_id] = {
        "filename": file.filename,
        "path": str(dest),
        "fields": filled_fields,
    }

    return TemplateAnalysisResponse(
        session_id=session_id,
        filename=file.filename,
        fields=[_field_to_out(f) for f in filled_fields],
    )


@app.post("/api/templates/update-fields")
def update_template_fields(update: UserInputUpdate):
    """Accept user corrections for uncertain/missing fields."""
    session = _template_sessions.get(update.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session nicht gefunden.")

    updated = apply_user_input(session["fields"], update.updates)
    session["fields"] = updated

    return {
        "session_id": update.session_id,
        "fields": [_field_to_out(f) for f in updated],
    }


@app.post("/api/templates/export/{session_id}")
def export_template(session_id: str):
    """Generate and return the filled template file."""
    session = _template_sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session nicht gefunden.")

    src_path = Path(session["path"])
    try:
        out_path = produce_filled_file(src_path, session["fields"])
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return FileResponse(
        path=str(out_path),
        filename=out_path.name,
        media_type="application/octet-stream",
    )


@app.get("/api/templates/session/{session_id}", response_model=TemplateAnalysisResponse)
def get_template_session(session_id: str):
    session = _template_sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session nicht gefunden.")
    return TemplateAnalysisResponse(
        session_id=session_id,
        filename=session["filename"],
        fields=[_field_to_out(f) for f in session["fields"]],
    )


# ── Startup: ingest pre-existing documents ────────────────────────────────────

@app.on_event("startup")
async def startup_ingest():
    """On startup, ingest documents in the background so server starts fast."""
    import asyncio, concurrent.futures
    loop = asyncio.get_event_loop()

    def _do_ingest():
        kb_results    = ingestion.ingest_directory(config.KNOWLEDGE_BASE_DIR, "knowledge_base")
        extra_results = ingestion.ingest_directory(config.ADDITIONAL_DOCS_DIR, "additional_documents")
        total = len(kb_results) + len(extra_results)
        print(f"[Startup] {total} Dokumente indiziert.", flush=True)
        for r in kb_results + extra_results:
            print(f"  • {r.get('file','?')} – {r.get('chunks',0)} Chunks ({r.get('status','?')})", flush=True)

    executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
    loop.run_in_executor(executor, _do_ingest)
    print("[Startup] Hintergrundindizierung gestartet.", flush=True)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _field_to_out(f: TemplateField) -> FieldOut:
    return FieldOut(
        field_id=f.field_id,
        label=f.label,
        location=f.location,
        current_value=f.current_value,
        filled_value=f.filled_value,
        citation=f.citation,
        confidence=f.confidence,
        status=f.status,
    )
