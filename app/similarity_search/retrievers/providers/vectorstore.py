from app.similarity_search.retrievers.base import BaseRetriever, ScoredDocs
from app.similarity_search.vectorstore.base import BaseVectorStore


class VectorStoreRetriever(BaseRetriever):
    """Dense retrieval delegated to the configured vector store."""

    def __init__(self, vectorstore_client: BaseVectorStore, **kwargs) -> None:
        """
        Parameters
        ----------
        vectorstore_client : BaseVectorStore
            Store whose ``query`` method performs the similarity search.
        **kwargs
            Unused; absorbed for registry compatibility.
        """
        self.vectorstore_client = vectorstore_client

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        score_normalization: str | None = None,
        metadata_filter: dict | None = None,
    ) -> ScoredDocs:
        """Run a dense similarity search and optionally normalise scores.

        Parameters
        ----------
        query : str
            User query string.
        top_k : int, optional
            Maximum results to return. Default is 5.
        score_normalization : str or None, optional
            Normalisation method (``minmax``, ``softmax``, etc.).
        metadata_filter : dict or None, optional
            Backend-specific filter forwarded to the vector store.

        Returns
        -------
        ScoredDocs
            List of ``(Document, score)`` pairs, highest similarity first.
        """
        scored = self.vectorstore_client.query(query, top_k, metadata_filter=metadata_filter)
        return self._apply_normalization(scored, score_normalization)
