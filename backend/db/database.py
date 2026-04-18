"""
database.py — SQLAlchemy async engine + TimescaleDB setup.
Also provides a cached DataFrame loader for the synthetic dataset.
"""
import logging
from functools import lru_cache
from pathlib import Path
from typing import Optional

import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from backend.config import DATABASE_URL

logger = logging.getLogger("chainmind.db")

# ─── Async SQLAlchemy engine ──────────────────────────────────────────────────
# SQLite doesn't support pool_size or max_overflow
engine_kwargs = {
    "echo": False,
    "pool_pre_ping": True,
}
if not DATABASE_URL.startswith("sqlite"):
    engine_kwargs.update({
        "pool_size": 5,
        "max_overflow": 10,
    })

engine = create_async_engine(DATABASE_URL, **engine_kwargs)

AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def init_db():
    """Initialize the database schema in Supabase."""
    from backend.db.schema import Base
    async with engine.begin() as conn:
        # We don't drop all in production, just create
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables initialized in Supabase.")


async def get_db() -> AsyncSession:
    """FastAPI dependency: yields async DB session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


# ─── Parquet cache (used when DB unavailable) ─────────────────────────────────
_DF_CACHE: Optional[pd.DataFrame] = None
PARQUET_PATH = Path(__file__).parent.parent / "data" / "synthetic_supply_chain.parquet"


async def get_df_cached() -> Optional[pd.DataFrame]:
    """
    Return cached supply chain DataFrame.
    Priority: 1) In-memory cache  2) PostgreSQL  3) Parquet file  4) Generated
    """
    global _DF_CACHE

    if _DF_CACHE is not None and len(_DF_CACHE) > 0:
        return _DF_CACHE

    # Try loading from parquet (fastest)
    if PARQUET_PATH.exists():
        try:
            _DF_CACHE = pd.read_parquet(PARQUET_PATH)
            logger.info("Loaded %d rows from parquet cache.", len(_DF_CACHE))
            return _DF_CACHE
        except Exception as exc:
            logger.warning("Parquet load failed: %s", exc)

    # Try loading from PostgreSQL
    try:
        async with AsyncSessionLocal() as session:
            from sqlalchemy import text
            from sqlalchemy.exc import OperationalError, ProgrammingError
            try:
                result = await session.execute(
                    text("SELECT * FROM supply_chain_daily LIMIT 200000")
                )
                rows = result.fetchall()
                if rows:
                    _DF_CACHE = pd.DataFrame(rows, columns=result.keys())
                    logger.info("Loaded %d rows from PostgreSQL.", len(_DF_CACHE))
                    return _DF_CACHE
            except (OperationalError, ProgrammingError):
                logger.info("No persistent supply_chain_daily database table found. Falling back to synthetic generation.")
    except Exception as exc:
        logger.warning("PostgreSQL connection error: %s. Generating synthetic data.", exc)

    # Fall back to generating synthetic data
    try:
        from backend.data.synthetic.generate_dataset import generate_and_save_sync
        _DF_CACHE = generate_and_save_sync()
        # Save to parquet for next time
        PARQUET_PATH.parent.mkdir(parents=True, exist_ok=True)
        _DF_CACHE.to_parquet(PARQUET_PATH, index=False)
        logger.info("Generated and cached %d synthetic rows.", len(_DF_CACHE))
        return _DF_CACHE
    except Exception as exc:
        logger.error("Data generation failed: %s", exc)
        return None


def invalidate_cache():
    """Clear the DataFrame cache to force a reload."""
    global _DF_CACHE
    _DF_CACHE = None
