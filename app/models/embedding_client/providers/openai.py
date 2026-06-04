from langchain_openai import OpenAIEmbeddings

from app.models.embedding_client.base import BaseEmbeddingClient
from app.models.embedding_client.registry import EmbeddingRegistry

_KNOWN_DIMS = {
    "text-embedding-3-small": 1536,
    "text-embedding-3-large": 3072,
    "text-embedding-ada-002": 1536,
}


@EmbeddingRegistry.register("openai")
class OpenAIEmbeddingClient(BaseEmbeddingClient):
    def __init__(self, cfg: dict):
        self._client = OpenAIEmbeddings(model=cfg["model"], api_key=cfg["api_key"])
        self._dim = cfg.get("dimensions") or _KNOWN_DIMS.get(cfg["model"], 1536)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self._client.embed_documents(list(texts))

    def embed_query(self, text: str) -> list[float]:
        return self._client.embed_query(text)

    @property
    def embedding_dim(self) -> int:
        return self._dim
