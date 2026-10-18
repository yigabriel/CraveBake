"""
Integration tests against a real, throwaway Postgres.

Run with the container from `docker-compose.test.yml`:

    TEST_DATABASE_URL=postgresql+asyncpg://cravebake:cravebake@localhost:55432/cravebake_test \
        pytest -m integration

Without `TEST_DATABASE_URL` every test here is skipped, so the default
`pytest` run stays database-free. The URL must point to localhost: these
tests drop the whole schema, so they refuse to run against anything else
(like the Supabase database in `.env`).

Isolation: the schema is rebuilt once per run with the real Alembic
migrations (which also seed units, conversions, categories and tags). Each
test then runs inside a transaction that is rolled back, so tests never see
each other's rows. Deferred constraints are only checked at COMMIT, which
never happens here, so they are forced with SET CONSTRAINTS ALL IMMEDIATE
before the rollback: a test that would break one at commit still fails.
"""
from __future__ import annotations

import asyncio
import os
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

import app.main  # noqa: F401  registers every ORM model, so foreign keys between modules resolve

BACKEND_DIR = Path(__file__).resolve().parents[2]
TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")
_SAFE_HOSTS = {"localhost", "127.0.0.1", "::1"}


def pytest_collection_modifyitems(config, items):
    for item in items:
        if Path(str(item.fspath)).is_relative_to(Path(__file__).parent):
            item.add_marker(pytest.mark.integration)
            if not TEST_DATABASE_URL:
                item.add_marker(pytest.mark.skip(reason="set TEST_DATABASE_URL to run integration tests"))


def run_alembic(*args: str) -> None:
    env = {**os.environ, "DATABASE_URL": TEST_DATABASE_URL}
    subprocess.run([sys.executable, "-m", "alembic", *args], cwd=BACKEND_DIR, env=env, check=True, capture_output=True)


async def _reset_schema() -> None:
    engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool)
    async with engine.begin() as connection:
        await connection.execute(text("DROP SCHEMA public CASCADE"))
        await connection.execute(text("CREATE SCHEMA public"))
    await engine.dispose()


@pytest.fixture(scope="session")
def migrated_database() -> str:
    host = urlparse(TEST_DATABASE_URL.replace("+asyncpg", "")).hostname
    if host not in _SAFE_HOSTS:
        pytest.exit(f"TEST_DATABASE_URL must point to localhost, not '{host}': these tests drop the schema.")
    asyncio.run(_reset_schema())
    run_alembic("upgrade", "head")
    return TEST_DATABASE_URL


@pytest.fixture
async def db_session(migrated_database):
    engine = create_async_engine(migrated_database, poolclass=NullPool)
    connection = await engine.connect()
    transaction = await connection.begin()
    session = AsyncSession(bind=connection, join_transaction_mode="create_savepoint", expire_on_commit=False)
    try:
        yield session
        if transaction.is_active:
            await session.flush()
            await connection.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))
    finally:
        await session.close()
        if transaction.is_active:
            await transaction.rollback()
        await connection.close()
        await engine.dispose()
