"""
LangGraph agent that orchestrates multi-step reasoning:
- Tool: search_knowledge_base
- Tool: search_additional_documents
- Tool: answer_from_context  (final synthesis)

The agent decides which collections to query and synthesises a grounded answer.
"""
from __future__ import annotations

import json
from typing import Annotated, Literal, TypedDict

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool
from langchain_ollama import ChatOllama
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages

import config
from ingestion import get_collection
from rag_chain import (
    SYSTEM_PROMPT,
    Citation,
    RAGResult,
    answer_question,
    retrieve_combined,
)

# ── State ─────────────────────────────────────────────────────────────────────

class AgentState(TypedDict):
    messages:    Annotated[list, add_messages]
    question:    str
    rag_result:  RAGResult | None


# ── Tools ─────────────────────────────────────────────────────────────────────

@tool
def search_knowledge_base(query: str) -> str:
    """Suche in der Wissensbasis (Gesetze, Konzessionsverträge, Masterpläne)."""
    from ingestion import _retrieve
    docs, metas, dists = _retrieve(query, config.COLLECTION_KB, top_k=4)
    if not docs:
        return "Keine Ergebnisse in der Wissensbasis gefunden."
    parts = []
    for doc, meta, dist in zip(docs, metas, dists):
        sim = max(0.0, 1.0 - dist / 2.0)
        parts.append(
            f"[Quelle: {meta.get('source_file','?')}, Seite {meta.get('page','?')}, "
            f"Relevanz: {sim:.2f}]\n{doc[:400]}"
        )
    return "\n\n---\n\n".join(parts)


@tool
def search_additional_documents(query: str) -> str:
    """Suche in den zusätzlich hochgeladenen Dokumenten (Leitfäden, Entwürfe, etc.)."""
    from ingestion import _retrieve
    docs, metas, dists = _retrieve(query, config.COLLECTION_EXTRA, top_k=4)
    if not docs:
        return "Keine Ergebnisse in den Zusatzdokumenten gefunden."
    parts = []
    for doc, meta, dist in zip(docs, metas, dists):
        sim = max(0.0, 1.0 - dist / 2.0)
        parts.append(
            f"[Quelle: {meta.get('source_file','?')}, Seite {meta.get('page','?')}, "
            f"Relevanz: {sim:.2f}]\n{doc[:400]}"
        )
    return "\n\n---\n\n".join(parts)


TOOLS = [search_knowledge_base, search_additional_documents]
TOOL_MAP = {t.name: t for t in TOOLS}


# ── LLM with tools ────────────────────────────────────────────────────────────

def get_agent_llm() -> ChatOllama:
    return ChatOllama(
        model=config.CHAT_MODEL,
        base_url=config.OLLAMA_BASE_URL,
        temperature=config.LLM_TEMPERATURE,
    ).bind_tools(TOOLS)


# ── Graph nodes ───────────────────────────────────────────────────────────────

AGENT_SYSTEM = """\
Du bist ein KI-Assistent für deutsche Kommunalverwaltungen (Energiewende/Wärmeplanung).

Du hast Zugriff auf zwei Suchwerkzeuge:
- search_knowledge_base: Suche in der kuratieren Wissensbasis (Gesetze, Verträge, Pläne)
- search_additional_documents: Suche in zusätzlich hochgeladenen Dokumenten

REGELN:
1. Rufe BEIDE Werkzeuge auf, wenn die Frage mehrere Dokumentenquellen betreffen könnte.
2. Basiere deine endgültige Antwort NUR auf den von den Werkzeugen zurückgegebenen Texten.
3. Erfinde keine Informationen.
4. Wenn keine relevanten Texte gefunden wurden, antworte: "ICH WEISS ES NICHT" und erkläre,
   welche zusätzlichen Informationen hilfreich wären.
5. Zitiere immer Quelle und Seite.
6. Antworte auf Deutsch.
"""


def agent_node(state: AgentState) -> AgentState:
    llm = get_agent_llm()
    messages = [SystemMessage(content=AGENT_SYSTEM)] + state["messages"]
    response = llm.invoke(messages)
    return {"messages": [response]}


def tool_node(state: AgentState) -> AgentState:
    last_msg = state["messages"][-1]
    results = []
    for tool_call in last_msg.tool_calls:
        tool_fn = TOOL_MAP.get(tool_call["name"])
        if tool_fn:
            output = tool_fn.invoke(tool_call["args"])
        else:
            output = f"Unbekanntes Werkzeug: {tool_call['name']}"
        results.append(ToolMessage(content=str(output), tool_call_id=tool_call["id"]))
    return {"messages": results}


def should_continue(state: AgentState) -> Literal["tools", "__end__"]:
    last = state["messages"][-1]
    if hasattr(last, "tool_calls") and last.tool_calls:
        return "tools"
    return "__end__"


# ── Build graph ───────────────────────────────────────────────────────────────

def build_agent_graph() -> StateGraph:
    graph = StateGraph(AgentState)
    graph.add_node("agent", agent_node)
    graph.add_node("tools", tool_node)
    graph.add_edge(START, "agent")
    graph.add_conditional_edges("agent", should_continue)
    graph.add_edge("tools", "agent")
    return graph.compile()


_agent_graph = None


def get_agent() -> StateGraph:
    global _agent_graph
    if _agent_graph is None:
        _agent_graph = build_agent_graph()
    return _agent_graph


# ── Public interface ──────────────────────────────────────────────────────────

def run_agent(question: str) -> RAGResult:
    """
    Run the LangGraph agent for a given question.
    Falls back to simple RAG if agent graph hits an error.
    """
    try:
        agent = get_agent()
        initial_state: AgentState = {
            "messages": [HumanMessage(content=question)],
            "question": question,
            "rag_result": None,
        }
        final_state = agent.invoke(initial_state)

        # Find the last AIMessage that has real text content (not just tool_calls)
        answer_text = ""
        for msg in reversed(final_state["messages"]):
            if isinstance(msg, AIMessage):
                content = msg.content if isinstance(msg.content, str) else ""
                # Skip messages that are purely tool-call dispatches (empty content or only JSON)
                if content and not _is_tool_call_only(content):
                    answer_text = content.strip()
                    break

        # If we still have nothing useful, fall back to simple RAG
        if not answer_text or _is_tool_call_only(answer_text):
            return answer_question(question)

        is_uncertain = "ICH WEISS ES NICHT" in answer_text.upper()

        # Extract citations from tool messages in the conversation
        citations = []
        for msg in final_state["messages"]:
            if isinstance(msg, ToolMessage):
                _parse_tool_citations(msg.content, citations)

        return RAGResult(
            answer=answer_text,
            citations=citations,
            is_uncertain=is_uncertain,
            clarification_request=(
                "Bitte laden Sie weitere Dokumente hoch oder präzisieren Sie Ihre Frage."
                if is_uncertain else None
            ),
        )
    except Exception as exc:
        # Fallback to simple RAG
        return answer_question(question)


def _is_tool_call_only(text: str) -> bool:
    """Return True if the text is just a raw tool-call JSON blob, not a real answer."""
    stripped = text.strip()
    # Detect patterns like [{"name": "search_knowledge_base", ...}]
    if stripped.startswith('[{') and '"name"' in stripped and '"arguments"' in stripped:
        return True
    if stripped.startswith('{"name"') and '"arguments"' in stripped:
        return True
    return False


def _parse_tool_citations(tool_output: str, citations: list[Citation]) -> None:
    """Extract citation metadata from tool output text."""
    import re
    pattern = r"\[Quelle:\s*([^,]+),\s*Seite\s*([^\],]+),\s*Relevanz:\s*([\d.]+)\]"
    for match in re.finditer(pattern, tool_output):
        src, page, score = match.groups()
        # Get excerpt: text after the bracket line
        start = match.end()
        excerpt = tool_output[start : start + 300].strip()
        citations.append(Citation(
            source_file=src.strip(),
            page=page.strip(),
            chunk_index=0,
            excerpt=excerpt,
            relevance_score=float(score),
        ))
