from app.models.llm_client.base import BaseLLMClient


class LLMRegistry:
    """Maps a provider name to its client class. Providers self-register via the decorator."""

    _clients: dict[str, type[BaseLLMClient]] = {}

    @classmethod
    def register(cls, name: str):
        def decorator(klass: type[BaseLLMClient]) -> type[BaseLLMClient]:
            cls._clients[name] = klass
            return klass

        return decorator

    @classmethod
    def create(cls, cfg: dict) -> BaseLLMClient:
        provider = cfg["provider"]
        klass = cls._clients.get(provider)
        if klass is None:
            raise ValueError(f"Unknown LLM provider {provider!r}. Registered: {list(cls._clients)}")
        return klass(cfg)
