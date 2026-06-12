from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from app.container import ServiceContainer


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield a per-request ``AsyncSession`` from the shared session factory.

    Yields
    ------
    AsyncSession
        SQLAlchemy async session; automatically closed after the request.
    """
    services = ServiceContainer.get_instance()
    async with services.session_factory() as session:
        yield session
