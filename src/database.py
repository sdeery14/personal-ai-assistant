"""Database connection and migration management."""

import asyncio
from pathlib import Path
from typing import Optional

import asyncpg
import structlog

from src.config import get_settings

logger = structlog.get_logger(__name__)

# Global connection pool
_pool: Optional[asyncpg.Pool] = None


async def get_pool() -> asyncpg.Pool:
    """Get or create the database connection pool.

    Returns:
        asyncpg connection pool

    Raises:
        RuntimeError: If pool is not initialized
    """
    global _pool
    if _pool is None:
        raise RuntimeError("Database pool not initialized. Call init_database() first.")
    return _pool


async def init_database() -> asyncpg.Pool:
    """Initialize the database connection pool.

    Returns:
        asyncpg connection pool
    """
    global _pool

    if _pool is not None:
        return _pool

    settings = get_settings()

    try:
        _pool = await asyncpg.create_pool(
            settings.postgres_url,
            min_size=2,
            max_size=10,
            command_timeout=60,
        )
        logger.info("database_pool_created", min_size=2, max_size=10)
        return _pool
    except Exception as e:
        logger.error("database_pool_creation_failed", error=str(e))
        raise


async def close_database() -> None:
    """Close the database connection pool."""
    global _pool

    if _pool is not None:
        await _pool.close()
        _pool = None
        logger.info("database_pool_closed")


async def run_migrations() -> None:
    """Run all SQL migrations in order.

    Migrations are idempotent (IF NOT EXISTS) and can be re-run safely.
    """
    pool = await get_pool()
    migrations_dir = Path(__file__).parent.parent / "migrations"

    if not migrations_dir.exists():
        logger.warning("migrations_directory_not_found", path=str(migrations_dir))
        return

    # Get all SQL files sorted by name
    migration_files = sorted(migrations_dir.glob("*.sql"))

    if not migration_files:
        logger.info("no_migrations_found")
        return

    async with pool.acquire() as conn:
        for migration_file in migration_files:
            try:
                sql = migration_file.read_text()
                await conn.execute(sql)
                logger.info(
                    "migration_applied",
                    file=migration_file.name,
                )
            except Exception as e:
                logger.error(
                    "migration_failed",
                    file=migration_file.name,
                    error=str(e),
                )
                raise


async def health_check() -> bool:
    """Check database connectivity.

    Returns:
        True if database is healthy, False otherwise
    """
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            result = await conn.fetchval("SELECT 1")
            return result == 1
    except Exception as e:
        logger.error("database_health_check_failed", error=str(e))
        return False
