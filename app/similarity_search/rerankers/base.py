from abc import ABC, abstractmethod

from app.similarity_search.retrievers.base import ScoredDocs


class BaseReranker(ABC):
    """Second-stage reorder of retrieved candidates against the query."""

    @abstractmethod
    def rerank(self, query: str, scored_docs: ScoredDocs, top_k: int = 5) -> ScoredDocs:
        ...
