from collections import defaultdict

from app.similarity_search.retrievers.base import BaseRetriever, ScoredDocs
from app.similarity_search.vectorstore.base import BaseVectorStore


class EnsembleRetriever(BaseRetriever):
    """Fuses dense and lexical results with Reciprocal Rank Fusion."""

    def __init__(
        self,
        vectorstore_client: BaseVectorStore,
        candidate_k: int = 20,
        rrf_k: int = 60,
        lexical_provider: str = "bm25",
        **kwargs,
    ) -> None:
        """
        Parameters
        ----------
        vectorstore_client : BaseVectorStore
            Backing store used by both sub-retrievers.
        candidate_k : int, optional
            Number of candidates each sub-retriever fetches before fusion. Default is 20.
        rrf_k : int, optional
            RRF rank-smoothing constant. Default is 60.
        lexical_provider : str, optional
            ``"bm25"`` (default) or ``"postgres_fts"``. When ``"postgres_fts"``,
            the store's ``conninfo`` attribute or a ``url`` kwarg must be present.
        **kwargs
            Forwarded to the lexical retriever; ``url`` is consumed when
            ``lexical_provider="postgres_fts"``.
        """
        from app.similarity_search.retrievers.providers.vectorstore import VectorStoreRetriever

        self.dense_retriever = VectorStoreRetriever(vectorstore_client)
        self.candidate_k = candidate_k
        self.rrf_k = rrf_k

        if lexical_provider == "postgres_fts":
            from app.similarity_search.retrievers.providers.postgres_fts import PostgresFTSRetriever

            url = kwargs.get("url") or getattr(vectorstore_client, "conninfo", None)
            self.lexical_retriever: BaseRetriever = PostgresFTSRetriever(
                vectorstore_client=vectorstore_client, url=url
            )
        else:
            from app.similarity_search.retrievers.providers.bm25 import BM25Retriever

            self.lexical_retriever = BM25Retriever(vectorstore_client)

    def _rrf(self, rank: int) -> float:
        """Compute the RRF score for a single rank position.

        Parameters
        ----------
        rank : int
            1-based rank of the document in one retriever's result list.

        Returns
        -------
        float
            ``1 / (rrf_k + rank)``.
        """
        return 1 / (self.rrf_k + rank)

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        score_normalization: str | None = None,
        metadata_filter: dict | None = None,
    ) -> ScoredDocs:
        """Retrieve and fuse results from dense and lexical arms via RRF.

        Parameters
        ----------
        query : str
            User query string.
        top_k : int, optional
            Final number of results to return after fusion. Default is 5.
        score_normalization : str or None, optional
            Normalisation method applied to the fused scores.
        metadata_filter : dict or None, optional
            Passed through to both sub-retrievers.

        Returns
        -------
        ScoredDocs
            Deduplicated, fused, and optionally normalised result list.
        """
        dense = self.dense_retriever.retrieve(query, top_k=self.candidate_k, metadata_filter=metadata_filter)
        lexical = self.lexical_retriever.retrieve(query, top_k=self.candidate_k, metadata_filter=metadata_filter)

        fused: dict = defaultdict(float)
        by_id: dict = {}
        for results in (dense, lexical):
            for rank, (doc, _) in enumerate(results, start=1):
                key = doc.metadata.get("id") or hash(doc.page_content)
                fused[key] += self._rrf(rank)
                by_id[key] = doc

        combined = sorted(
            ((by_id[k], s) for k, s in fused.items()), key=lambda pair: pair[1], reverse=True
        )
        combined = self._apply_normalization(combined, score_normalization)
        return combined[:top_k]
