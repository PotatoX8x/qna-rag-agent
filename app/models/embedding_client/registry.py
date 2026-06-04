from app.models.embedding_client.base import BaseEmbeddingClient


class EmbeddingRegistry:
    """Maps a provider name to its embedding client class."""

    _clients: dict[str, type[BaseEmbeddingClient]] = {}

    @classmethod
    def register(cls, name: str):
        def decorator(klass: type[BaseEmbeddingClient]) -> type[BaseEmbeddingClient]:
            cls._clients[name] = klass
            return klass

        return decorator

    @classmethod
    def create(cls, cfg: dict) -> BaseEmbeddingClient:
        provider = cfg["provider"]
        klass = cls._clients.get(provider)
        if klass is None:
            raise ValueError(f"Unknown embedding provider {provider!r}. Registered: {list(cls._clients)}")
        return klass(cfg)
