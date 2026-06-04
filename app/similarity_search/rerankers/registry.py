from app.similarity_search.rerankers.base import BaseReranker


class RerankerRegistry:
    """Maps a reranker name to its class. Providers self-register via the decorator."""

    _rerankers: dict[str, type[BaseReranker]] = {}

    @classmethod
    def register(cls, name: str):
        def decorator(klass: type[BaseReranker]) -> type[BaseReranker]:
            cls._rerankers[name] = klass
            return klass

        return decorator

    @classmethod
    def create(cls, name: str, cfg: dict | None = None) -> BaseReranker:
        klass = cls._rerankers.get(name)
        if klass is None:
            raise ValueError(f"Unknown reranker {name!r}. Registered: {list(cls._rerankers)}")
        return klass(cfg or {})
