import threading
from dataclasses import dataclass
from pathlib import Path

from app.core.config import load_config
from app.core.logging import setup_logging
from app.core.observability import setup_observability


@dataclass
class AppServices:
    config: dict


class ServiceContainer:
    """Composition root. Builds the shared services once and hands out the same instance.

    Later phases extend ``AppServices`` with the database session factory, LLM and
    embedding clients, vector store and web search — all constructed here so the rest
    of the app depends on instances rather than wiring its own.
    """

    _instance: AppServices | None = None
    _lock = threading.Lock()

    @classmethod
    def get_instance(cls) -> AppServices:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls._build()
        return cls._instance

    @classmethod
    def _build(cls) -> AppServices:
        config = load_config()
        setup_logging(config.get("logging", {}))
        setup_observability(config)

        Path(config["database"]["data_dir"]).mkdir(parents=True, exist_ok=True)

        return AppServices(config=config)

    @classmethod
    def reset(cls) -> None:
        with cls._lock:
            cls._instance = None
