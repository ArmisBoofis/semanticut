"""
Test env: skip real DB startup; use a dummy DATABASE_URL so Settings / engine load.
"""

import os

os.environ["DATABASE_URL"] = "postgresql+asyncpg://test:test@127.0.0.1:5432/test"
os.environ["SKIP_DB_STARTUP"] = "1"
