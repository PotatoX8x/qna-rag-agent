from typing import TypedDict

from langchain_core.documents import Document

ScoredDoc = tuple[Document, float]


class AgentState(TypedDict):
    """Mutable bag-of-state threaded through every LangGraph node."""

    query: str
    kb_id: str
    history: list[dict]
    documents: list[ScoredDoc]
    answer: str
    citations: list[dict]
    needs_web_search: bool
    generation_count: int
    hallucination_detected: bool
    retrieved_count: int
