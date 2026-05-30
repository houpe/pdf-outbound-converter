import sys
from pathlib import Path

import pytest

backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

import database


class TestInitDbCreatesTables:

    def test_split_codes_created(self, tmp_path):
        db_path = tmp_path / "test_init.db"
        conn = database.sqlite3.connect(str(db_path))
        conn.close()

        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(database, "DB_PATH", db_path)
            database.init_db()

        conn = database.sqlite3.connect(str(db_path))
        tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
        conn.close()
        assert "split_codes" in tables

    def test_hlmc_sequences_created(self, tmp_path, monkeypatch):
        db_path = tmp_path / "test_hlmc.db"
        conn = database.sqlite3.connect(str(db_path))
        conn.close()

        monkeypatch.setattr(database, "DB_PATH", db_path)
        database.init_db()

        conn = database.sqlite3.connect(str(db_path))
        tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
        conn.close()
        assert "hlmc_sequences" in tables

    def test_hlmc_history_created(self, tmp_path, monkeypatch):
        db_path = tmp_path / "test_hist.db"
        conn = database.sqlite3.connect(str(db_path))
        conn.close()

        monkeypatch.setattr(database, "DB_PATH", db_path)
        database.init_db()

        conn = database.sqlite3.connect(str(db_path))
        tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
        conn.close()
        assert "hlmc_history" in tables


class TestGetHlmcOrder:

    @pytest.fixture
    def hlmc_conn(self, tmp_path, monkeypatch):
        db_path = tmp_path / "test_seq.db"
        conn = database.sqlite3.connect(str(db_path))
        conn.execute("""
            CREATE TABLE IF NOT EXISTS split_codes (code TEXT PRIMARY KEY)
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS hlmc_sequences (date TEXT NOT NULL, prefix TEXT NOT NULL, seq INTEGER NOT NULL DEFAULT 1, PRIMARY KEY (date, prefix))
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS hlmc_history (id INTEGER PRIMARY KEY AUTOINCREMENT, shop_name TEXT, date TEXT NOT NULL, signature TEXT NOT NULL UNIQUE, order_no TEXT NOT NULL)
        """)
        conn.commit()
        conn.close()

        def mock_get_db():
            c = database.sqlite3.connect(str(db_path))
            c.row_factory = database.sqlite3.Row
            return c

        monkeypatch.setattr(database, "get_db", mock_get_db)
        monkeypatch.setattr(database, "DB_PATH", db_path)
        return

    def test_first_call_returns_0001(self, hlmc_conn):
        assert database.get_hlmc_order("银泰", "260502", "sig1", "YT") == "YT2605020001"

    def test_same_signature_returns_cached(self, hlmc_conn):
        first = database.get_hlmc_order("金桥", "260502", "cached_sig", "JQ")
        assert database.get_hlmc_order("金桥", "260502", "cached_sig", "JQ") == first

    def test_different_signature_increments(self, hlmc_conn):
        no1 = database.get_hlmc_order("银泰", "260503", "sig_a", "YT")
        no2 = database.get_hlmc_order("银泰", "260503", "sig_b", "YT")
        assert no1 == "YT2605030001"
        assert no2 == "YT2605030002"
