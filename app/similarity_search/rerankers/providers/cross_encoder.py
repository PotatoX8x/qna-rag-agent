from app.similarity_search.rerankers.base import BaseReranker
from app.similarity_search.rerankers.registry import RerankerRegistry
from app.similarity_search.retrievers.base import ScoredDocs


@RerankerRegistry.register("cross_encoder")
class CrossEncoderReranker(BaseReranker):
    """Scores each (query, document) pair with a cross-encoder. Needs sentence-transformers."""

    def __init__(self, cfg: dict | None = None):
        cfg = cfg or {}
        try:
            from sentence_transformers import CrossEncoder
        except ImportError as exc:
            raise ImportError(
                "Reranker 'cross_encoder' requires the sentence-transformers package."
            ) from exc

        self._model = CrossEncoder(cfg.get("model", "cross-encoder/ms-marco-MiniLM-L-6-v2"))

    def rerank(self, query: str, scored_docs: ScoredDocs, top_k: int = 5) -> ScoredDocs:
        if not scored_docs:
            return []
        documents = [doc for doc, _ in scored_docs]
        scores = self._model.predict([(query, doc.page_content) for doc in documents])
        reranked = sorted(zip(documents, scores), key=lambda pair: pair[1], reverse=True)
        return [(doc, float(score)) for doc, score in reranked][:top_k]
