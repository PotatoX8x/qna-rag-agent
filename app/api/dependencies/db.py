from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from app.container import ServiceContainer


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    services = ServiceContainer.get_instance()
    async with services.session_factory() as session:
        yield session
