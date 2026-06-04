from abc import ABC, abstractmethod


class BaseEmbeddingClient(ABC):
    """Provider-agnostic embedding interface."""

    @abstractmethod
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of documents."""

    @abstractmethod
    def embed_query(self, text: str) -> list[float]:
        """Embed a single query."""

    @property
    @abstractmethod
    def embedding_dim(self) -> int:
        """Dimensionality of the produced vectors; used to size the vector column."""
