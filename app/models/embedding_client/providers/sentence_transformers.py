from app.models.embedding_client.base import BaseEmbeddingClient
from app.models.embedding_client.registry import EmbeddingRegistry

_KNOWN_DIMS = {
    "all-MiniLM-L6-v2": 384,
    "all-MiniLM-L12-v2": 384,
    "all-mpnet-base-v2": 768,
    "paraphrase-multilingual-MiniLM-L12-v2": 384,
    "BAAI/bge-small-en-v1.5": 384,
    "BAAI/bge-base-en-v1.5": 768,
}


@EmbeddingRegistry.register("sentence_transformers")
class SentenceTransformerEmbeddingClient(BaseEmbeddingClient):
    """Local, offline embeddings. The model is loaded on first use so constructing
    the client (and the container) stays cheap and import-free."""

    def __init__(self, cfg: dict):
        self._model_name = cfg.get("model", "all-MiniLM-L6-v2")
        self._configured_dim = cfg.get("dimensions") or _KNOWN_DIMS.get(self._model_name)
        self._model = None

    def _ensure_model(self):
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
            except ImportError as exc:
                raise ImportError(
                    "Provider 'sentence_transformers' requires the sentence-transformers package."
                ) from exc
            self._model = SentenceTransformer(self._model_name)
        return self._model

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self._ensure_model().encode(list(texts), normalize_embeddings=True).tolist()

    def embed_query(self, text: str) -> list[float]:
        return self._ensure_model().encode(text, normalize_embeddings=True).tolist()

    @property
    def embedding_dim(self) -> int:
        if self._configured_dim is not None:
            return self._configured_dim
        return self._ensure_model().get_sentence_embedding_dimension()
