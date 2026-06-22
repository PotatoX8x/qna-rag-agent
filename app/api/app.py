import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api.limiter import limiter
from app.api.routers import health, auth, knowledge_bases, documents, conversations
from app.container import ServiceContainer
from app.core.observability import setup_observability
from app.core.paths import detect_project_root

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    services = ServiceContainer.get_instance()
    app.state.services = services

    setup_observability(services.config)

    from app.agent.graph import build_graph
    app.state.agent_graph = build_graph(services)

    logger.info("Services initialized")
    yield
    logger.info("Shutdown complete")


def create_app() -> FastAPI:
    """Construct and configure the FastAPI application.

    Returns
    -------
    FastAPI
        Fully configured application instance.
    """
    app = FastAPI(
        title="QnA RAG Agent",
        version="0.1.0",
        docs_url=None,
        redoc_url=None,
        lifespan=lifespan,
    )

    services = ServiceContainer.get_instance()

    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    origins = services.config["api"]["allowed_origins"]
    if isinstance(origins, str):
        origins = [o.strip() for o in origins.split(",")]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(Exception)
    async def on_unhandled(request: Request, exc: Exception):
        logger.exception("Unhandled error on %s %s", request.method, request.url.path)
        return JSONResponse(status_code=500, content={"detail": "Internal server error"})

    app.include_router(health.router, prefix="/api")
    app.include_router(auth.router, prefix="/api")
    app.include_router(knowledge_bases.router, prefix="/api")
    app.include_router(documents.router, prefix="/api")
    app.include_router(conversations.router, prefix="/api")

    web_dir = detect_project_root() / "web"
    if (web_dir / "assets").is_dir():
        app.mount("/assets", StaticFiles(directory=web_dir / "assets"), name="assets")

    @app.get("/", include_in_schema=False)
    async def index():
        index_html = web_dir / "index.html"
        if index_html.exists():
            return FileResponse(index_html)
        return JSONResponse({"service": "qna-rag-agent", "status": "ok"})

    @app.get("/app", include_in_schema=False)
    async def app_page():
        app_html = web_dir / "app.html"
        if app_html.exists():
            return FileResponse(app_html)
        return JSONResponse({"service": "qna-rag-agent", "status": "ok"})

    return app


app = create_app()
