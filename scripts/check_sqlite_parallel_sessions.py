"""Run with: python scripts/check_sqlite_parallel_sessions.py"""
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import text
from sqlalchemy.pool import NullPool

from backend.control_plane.database import configure_database, get_engine, session_scope


with tempfile.TemporaryDirectory() as root:
    configure_database(f"sqlite:///{Path(root, 'parallel.db').as_posix()}")
    assert isinstance(get_engine().pool, NullPool)
    barrier = Barrier(12)

    def read_at_once(_index):
        with session_scope() as session:
            assert session.execute(text("SELECT 1")).scalar_one() == 1
            barrier.wait(timeout=10)
            return session.execute(text("SELECT 1")).scalar_one()

    with ThreadPoolExecutor(max_workers=12) as executor:
        assert list(executor.map(read_at_once, range(12))) == [1] * 12
    get_engine().dispose()

print("SQLite parallel session check passed")
