from abc import abstractmethod

from langchain_core.embeddings import Embeddings


class BaseEmbeddingClient(Embeddings):
    """Provider-agnostic embedding interface.

    Extends ``langchain_core.embeddings.Embeddings`` so any LangChain tool
    (``SemanticChunker``, vectorstores, etc.) can consume it without an adapter.
    """

    @abstractmethod
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of documents.

        Parameters
        ----------
        texts : list[str]
            Passages to embed.

        Returns
        -------
        list[list[float]]
            One embedding vector per input text, in the same order.
        """

    @abstractmethod
    def embed_query(self, text: str) -> list[float]:
        """Embed a single query string.

        Parameters
        ----------
        text : str
            Query to embed.

        Returns
        -------
        list[float]
            Embedding vector.
        """

    @property
    @abstractmethod
    def embedding_dim(self) -> int:
        """Dimensionality of the produced vectors.

        Returns
        -------
        int
            Vector length, used to size the pgvector column.
        """
