"""One-time / startup DB initialization.

Creates the extensions and schema this app depends on, then creates any
tables (and enum types) that don't exist yet.

This is meant for local dev and first boot. In staging/prod, prefer Alembic
migrations over init_db()'s create_all -- create_all can create missing
tables but never alters existing ones, so it silently stops being useful
the moment you need a real schema change.
"""

from __future__ import annotations

import logging

from sqlalchemy import text

from app.core.config import settings
from app.database.base import Base
from app.database.session import engine

# Import every model module so they register on Base.metadata before
# create_all runs. See models/__init__.py.
import app.database.models  # noqa: F401

logger = logging.getLogger(__name__)


async def init_db() -> None:
    async with engine.begin() as conn:
        # gen_random_uuid() is native to Postgres 13+, pgcrypto is kept for
        # older Postgres and other crypto helpers. "vector" is pgvector itself.
        await conn.execute(text('CREATE EXTENSION IF NOT EXISTS "pgcrypto"'))
        await conn.execute(text('CREATE EXTENSION IF NOT EXISTS "vector"'))
        await conn.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{settings.POSTGRES_SCHEMA}"'))
        await conn.run_sync(Base.metadata.create_all)

    logger.info("init_db: schema %r ready (%s)", settings.POSTGRES_SCHEMA, settings.database_dsn)


async def dispose_db() -> None:
    """Call on app shutdown to close pooled connections cleanly."""
    await engine.dispose()