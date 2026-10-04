"""
RAG retrieval helpers.
Performs similarity search in ChromaDB and returns
(answer, citations) pairs via the local Mistral model.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from langchain_ollama import ChatOllama, OllamaEmbeddings

import config
from ingestion import get_collection

# ── Data models ───────────────────────────────────────────────────────────────

@dataclass
class Citation:
    source_file: str
    page: str
    chunk_index: int
    excerpt: str          # first 300 chars of the chunk
    relevance_score: float


@dataclass
class RAGResult:
    answer: str
    citations: list[Citation] = field(default_factory=list)
    is_uncertain: bool = False
    clarification_request: Optional[str] = None


# ── System prompt ─────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """\
Du bist ein spezialisierter KI-Assistent für deutsche Kommunalverwaltungen im Bereich
Energiewende und kommunale Wärmeplanung. Du hilfst Sachbearbeitern, Gesetze, Verträge
und Pläne schnell zu verstehen und Informationen daraus zu extrahieren.

REGELN:
1. Beantworte die Frage so VOLLSTÄNDIG und DETAILLIERT wie möglich auf Basis der Dokumentenauszüge.
2. Fasse alle relevanten Informationen aus ALLEN bereitgestellten Auszügen zusammen – übersieht nichts.
3. Zitiere nach jeder wichtigen Aussage die Quelle in Klammern: (Dokumentname, Seite X).
4. Strukturiere lange Antworten mit Aufzählungen oder Abschnitten.
5. Nur wenn die Antwort wirklich nicht in den Auszügen steht: Schreibe „ICH WEISS ES NICHT“
   und erkläre genau, welche zusätzlichen Informationen fehlen.
6. Antworte IMMER auf Deutsch.
7. Direkte Zitate aus den Dokumenten in Anführungszeichen.
"""

HUMAN_TEMPLATE = """\
Folgende Dokumentenauszüge stehen zur Verfügung:

{context}

---

Frage des Nutzers: {question}

Aufgabe: Lies alle Auszüge sorgfältig durch und beantworte die Frage vollständig und strukturiert.
Nutze alle relevanten Informationen aus den Auszügen. Gib nach jeder Aussage die Quelle an
(Dokumentname, Seite). Wenn du dir bei einzelnen Punkten unsicher bist, kennzeichne dies.
Nur wenn KEINE der Fragen aus den Auszügen beantwortet werden kann: Schreibe "ICH WEISS ES NICHT".
"""


# ── LLM singleton ─────────────────────────────────────────────────────────────

_llm: ChatOllama | None = None


def get_llm() -> ChatOllama:
    global _llm
    if _llm is None:
        _llm = ChatOllama(
            model=config.CHAT_MODEL,
            base_url=config.OLLAMA_BASE_URL,
            temperature=config.LLM_TEMPERATURE,
            num_predict=getattr(config, 'LLM_NUM_PREDICT', 1024),
            num_ctx=4096,      # Mistral 7B sweet-spot: fast + enough context
            #repeat_penalty=1.1,
        )
    return _llm


# ── Retrieval ─────────────────────────────────────────────────────────────────

def _retrieve(query: str, collection_name: str, top_k: int = config.TOP_K_RETRIEVAL):
    """Return (documents, metadatas, distances) from ChromaDB."""
    col = get_collection(collection_name)
    count = col.count()
    if count == 0:
        return [], [], []
    actual_k = min(top_k, count)
    results = col.query(
        query_texts=[query],
        n_results=actual_k,
        include=["documents", "metadatas", "distances"],
    )
    docs      = results["documents"][0]      if results["documents"]  else []
    metas     = results["metadatas"][0]      if results["metadatas"]  else []
    distances = results["distances"][0]      if results["distances"]  else []
    return docs, metas, distances


def retrieve_combined(query: str) -> tuple[list[str], list[dict], list[float]]:
    """Retrieve from both KB and additional-docs collections."""
    docs_kb,   metas_kb,   dists_kb   = _retrieve(query, config.COLLECTION_KB)
    docs_ex,   metas_ex,   dists_ex   = _retrieve(query, config.COLLECTION_EXTRA)

    combined = list(zip(docs_kb + docs_ex, metas_kb + metas_ex, dists_kb + dists_ex))
    # Sort ascending by distance (lower = more similar for cosine)
    combined.sort(key=lambda x: x[2])
    combined = combined[: config.TOP_K_RETRIEVAL]

    if not combined:
        return [], [], []
    docs, metas, dists = zip(*combined)
    return list(docs), list(metas), list(dists)


# ── Main RAG function ─────────────────────────────────────────────────────────

def answer_question(question: str) -> RAGResult:
    """
    Main entry point: retrieve relevant chunks, call LLM, return RAGResult.
    If no relevant context is found above the threshold, returns uncertain result.
    """
    docs, metas, dists = retrieve_combined(question)

    # ChromaDB cosine distance: 0 = identical, 2 = opposite.
    # Convert to similarity: sim = 1 - dist/2  (range 0..1)
    def to_sim(d: float) -> float:
        return max(0.0, 1.0 - d / 2.0)

    relevant_chunks = [
        (doc, meta, to_sim(dist))
        for doc, meta, dist in zip(docs, metas, dists)
        if to_sim(dist) >= config.MIN_RELEVANCE_SCORE
    ]

    if not relevant_chunks:
        return RAGResult(
            answer="ICH WEISS ES NICHT",
            is_uncertain=True,
            clarification_request=(
                "Für diese Frage wurden keine ausreichend relevanten Informationen "
                "in der Wissensbasis gefunden. Bitte laden Sie weitere Dokumente hoch "
                "oder präzisieren Sie Ihre Frage."
            ),
        )

    # Build context string for the prompt
    context_parts = []
    citations = []
    for i, (doc, meta, sim) in enumerate(relevant_chunks, start=1):
        src  = meta.get("source_file", "Unbekannt")
        page = meta.get("page", "?")
        context_parts.append(
            f"[Auszug {i}] Quelle: {src}, Seite {page}\n"
            f"{'-'*60}\n"
            f"{doc}\n"
        )
        citations.append(Citation(
            source_file=src,
            page=str(page),
            chunk_index=int(meta.get("chunk_index", 0)),
            excerpt=doc[:500],   # show more in the UI
            relevance_score=round(sim, 3),
        ))

    context_str = "\n\n---\n\n".join(context_parts)
    human_msg   = HUMAN_TEMPLATE.format(context=context_str, question=question)

    from langchain_core.messages import HumanMessage, SystemMessage
    llm = get_llm()
    response = llm.invoke([
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=human_msg),
    ])
    answer_text = response.content.strip()

    # Detect if model itself flagged uncertainty
    is_uncertain = "ICH WEISS ES NICHT" in answer_text.upper()

    clarification = None
    if is_uncertain:
        clarification = (
            "Bitte laden Sie weitere relevante Dokumente hoch oder "
            "stellen Sie Ihre Frage mit mehr Kontext."
        )

    return RAGResult(
        answer=answer_text,
        citations=citations,
        is_uncertain=is_uncertain,
        clarification_request=clarification,
    )
