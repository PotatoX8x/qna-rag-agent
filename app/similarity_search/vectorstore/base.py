from abc import ABC, abstractmethod
from typing import Optional

from langchain_core.documents import Document


class BaseVectorStore(ABC):
    """Storage and dense-similarity interface over a single collection."""

    @abstractmethod
    def add_documents(self, documents: list[Document]) -> None:
        ...

    @abstractmethod
    def query(
        self,
        query: str,
        top_k: int = 5,
        metadata_filter: Optional[dict] = None,
    ) -> list[tuple[Document, float]]:
        """Dense search returning ``(document, similarity)`` pairs, highest first."""

    @abstractmethod
    def get_collection(self, metadata_filter: Optional[dict] = None) -> list[Document]:
        """Return stored documents, optionally narrowed by a metadata filter."""

    @abstractmethod
    def clear(self) -> None:
        ...

    @abstractmethod
    def reset_collection(self) -> None:
        ...
