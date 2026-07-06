from app.file_store.base import BaseFileStore


class FileStoreRegistry:
    """Maps a provider name to its file store class."""

    _stores: dict[str, type[BaseFileStore]] = {}

    @classmethod
    def register(cls, name: str):
        def decorator(klass: type[BaseFileStore]) -> type[BaseFileStore]:
            cls._stores[name] = klass
            return klass

        return decorator

    @classmethod
    def create(cls, cfg: dict) -> BaseFileStore:
        provider = cfg["provider"]
        klass = cls._stores.get(provider)
        if klass is None:
            raise ValueError(f"Unknown file store provider {provider!r}. Registered: {list(cls._stores)}")
        return klass(cfg)
