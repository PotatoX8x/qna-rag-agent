import threading
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.core.config import load_config
from app.core.logging import setup_logging
from app.core.observability import setup_observability
from app.db.engine import create_engine_and_session
from app.models.embedding_client import EmbeddingRegistry
from app.models.embedding_client.base import BaseEmbeddingClient
from app.models.llm_client import LLMRegistry
from app.models.llm_client.base import BaseLLMClient


@dataclass
class AppServices:
    config: dict
    llm: BaseLLMClient
    embeddings: BaseEmbeddingClient
    engine: AsyncEngine
    session_factory: async_sessionmaker[AsyncSession]


class ServiceContainer:
    """Composition root. Builds shared services once; hands out the same instance.

    Extended in later phases with vector store and web search.
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

        llm = LLMRegistry.create(config["models"]["llm"])
        embeddings = EmbeddingRegistry.create(config["models"]["embeddings"])
        engine, session_factory = create_engine_and_session(config["database"]["url"])

        return AppServices(
            config=config,
            llm=llm,
            embeddings=embeddings,
            engine=engine,
            session_factory=session_factory,
        )

    @classmethod
    def reset(cls) -> None:
        with cls._lock:
            cls._instance = None
