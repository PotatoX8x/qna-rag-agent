from app.similarity_search.rerankers.base import BaseReranker
from app.similarity_search.rerankers.registry import RerankerRegistry
from app.similarity_search.retrievers.base import ScoredDocs


@RerankerRegistry.register("cross_encoder")
class CrossEncoderReranker(BaseReranker):
    """Second-stage reranker using a cross-encoder model from ``sentence-transformers``."""

    def __init__(self, cfg: dict | None = None):
        """
        Parameters
        ----------
        cfg : dict or None, optional
            Config block. Reads ``model`` (default ``cross-encoder/ms-marco-MiniLM-L-6-v2``).

        Raises
        ------
        ImportError
            When ``sentence-transformers`` is not installed.
        """
        cfg = cfg or {}
        try:
            from sentence_transformers import CrossEncoder
        except ImportError as exc:
            raise ImportError(
                "Reranker 'cross_encoder' requires the sentence-transformers package."
            ) from exc

        self._model = CrossEncoder(cfg.get("model", "cross-encoder/ms-marco-MiniLM-L-6-v2"))

    def rerank(self, query: str, scored_docs: ScoredDocs, top_k: int = 5) -> ScoredDocs:
        """Score each (query, document) pair and return the top-k by cross-encoder score.

        Parameters
        ----------
        query : str
            The user query.
        scored_docs : ScoredDocs
            Candidate documents from a first-stage retriever.
        top_k : int, optional
            Number of documents to return. Default is 5.

        Returns
        -------
        ScoredDocs
            Re-ordered subset of ``scored_docs``, highest cross-encoder score first.
        """
        if not scored_docs:
            return []
        documents = [doc for doc, _ in scored_docs]
        scores = self._model.predict([(query, doc.page_content) for doc in documents])
        reranked = sorted(zip(documents, scores), key=lambda pair: pair[1], reverse=True)
        return [(doc, float(score)) for doc, score in reranked][:top_k]
