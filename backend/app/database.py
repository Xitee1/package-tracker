import asyncio
import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine, AsyncSession
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

logger = logging.getLogger(__name__)

engine = create_async_engine(settings.database_url)
async_session = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def wait_for_db(
    max_retries: int = 10,
    initial_delay: float = 1.0,
    max_delay: float = 30.0,
) -> None:
    """Wait for the database to become available with exponential backoff."""
    delay = initial_delay
    for attempt in range(1, max_retries + 1):
        try:
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            logger.info("Database is ready.")
            return
        except Exception as exc:
            if attempt == max_retries:
                logger.error("Could not connect to database after %d attempts.", max_retries)
                raise
            logger.warning(
                "Database not ready (attempt %d/%d): %s. Retrying in %.1fs…",
                attempt, max_retries, exc, delay,
            )
            await asyncio.sleep(delay)
            delay = min(delay * 2, max_delay)


async def get_db() -> AsyncSession:
    async with async_session() as session:
        yield session
