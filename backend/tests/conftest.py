"""
Shared test setup.

Settings are required at import time (`app.shared.database.session` builds
the engine on import), so dummy values are provided before anything from
`app` is imported. No test opens a database connection: repositories are
replaced by in-memory fakes.
"""
import os

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost:5432/test")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key")
