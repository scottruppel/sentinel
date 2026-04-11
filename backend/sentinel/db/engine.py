from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine

from sentinel.config import settings

engine: AsyncEngine = create_async_engine(
    settings.database_url,
    echo=False,
    pool_size=5,
    max_overflow=10,
)
