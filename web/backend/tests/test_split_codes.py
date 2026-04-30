"""
Tests for split codes CRUD API endpoints.
"""

import os
import sys
import sqlite3
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient

# Add backend to path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from main import app
from database import get_db


@pytest.fixture
def test_db(tmp_path: Path):
    """
    Creates a temporary test database for each test.
    """
    db_path = tmp_path / "test_split_codes.db"
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE IF NOT EXISTS split_codes (
            code TEXT PRIMARY KEY COLLATE NOCASE,
            split TEXT NOT NULL DEFAULT '是',
            item_name TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
        )
    """)
    conn.commit()
    conn.close()
    return db_path


@pytest.fixture
def client_with_db(test_db: Path):
    """
    Creates a TestClient with the test database.
    Patches both DB_PATH and init_db to prevent real database usage.
    """
    def create_test_db():
        conn = sqlite3.connect(str(test_db))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def noop_init_db():
        """No-op init_db for tests"""
        pass

    # Patch multiple modules to prevent real database access
    with patch("database.DB_PATH", test_db), \
         patch("database.get_db", create_test_db), \
         patch("config.DB_PATH", test_db), \
         patch("main.init_db", noop_init_db):
        client = TestClient(app)
        yield client, test_db


class TestListSplitCodes:
    """Tests for GET /api/split-codes endpoint."""

    def test_list_empty(self, client_with_db):
        """Test listing codes when database is empty."""
        client, _ = client_with_db
        response = client.get("/api/split-codes")

        assert response.status_code == 200
        data = response.json()
        assert data["codes"] == []
        assert data["total"] == 0

    def test_list_with_codes(self, client_with_db, test_db: Path):
        """Test listing codes when database has entries."""
        client, db_path = client_with_db

        # Insert some test codes directly
        conn = sqlite3.connect(str(db_path))
        conn.execute("INSERT INTO split_codes (code, split) VALUES ('TEST001', '是')")
        conn.execute("INSERT INTO split_codes (code, split) VALUES ('TEST002', '否')")
        conn.commit()
        conn.close()

        response = client.get("/api/split-codes")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        codes = {c["code"] for c in data["codes"]}
        assert "TEST001" in codes
        assert "TEST002" in codes


class TestCreateSplitCode:
    """Tests for POST /api/split-codes endpoint."""

    def test_create_valid(self, client_with_db):
        """Test creating a valid split code."""
        client, _ = client_with_db
        response = client.post(
            "/api/split-codes",
            json={"code": "NEWCODE001", "split": "是"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["code"] == "NEWCODE001"
        assert data["split"] == "是"

    def test_create_with_split_no(self, client_with_db):
        """Test creating a split code with '否' value."""
        client, _ = client_with_db
        response = client.post(
            "/api/split-codes",
            json={"code": "NEWCODE002", "split": "否"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["split"] == "否"

    def test_create_duplicate(self, client_with_db, test_db: Path):
        """Test creating a duplicate code returns 409."""
        client, db_path = client_with_db

        # Insert a code first
        conn = sqlite3.connect(str(db_path))
        conn.execute("INSERT INTO split_codes (code, split) VALUES ('DUPCODE', '是')")
        conn.commit()
        conn.close()

        # Try to create the same code
        response = client.post(
            "/api/split-codes",
            json={"code": "DUPCODE", "split": "否"},
        )

        assert response.status_code == 409
        assert "已存在" in response.json()["detail"]

    def test_create_empty_code(self, client_with_db):
        """Test creating with empty code returns 400."""
        client, _ = client_with_db
        response = client.post(
            "/api/split-codes",
            json={"code": "", "split": "是"},
        )

        assert response.status_code == 400
        assert "不能为空" in response.json()["detail"]

    def test_create_whitespace_code(self, client_with_db):
        """Test creating with whitespace-only code returns 400."""
        client, _ = client_with_db
        response = client.post(
            "/api/split-codes",
            json={"code": "   ", "split": "是"},
        )

        assert response.status_code == 400
        assert "不能为空" in response.json()["detail"]

    def test_create_invalid_split_value(self, client_with_db):
        """Test creating with invalid split value returns 400."""
        client, _ = client_with_db
        response = client.post(
            "/api/split-codes",
            json={"code": "VALIDCODE", "split": "maybe"},
        )

        assert response.status_code == 400
        assert "拆零值必须为「是」或「否」" in response.json()["detail"]

    def test_create_code_trimmed(self, client_with_db):
        """Test that code is trimmed on creation."""
        client, _ = client_with_db
        response = client.post(
            "/api/split-codes",
            json={"code": "  TRIMMED001  ", "split": "是"},
        )

        assert response.status_code == 200
        assert response.json()["code"] == "TRIMMED001"


class TestDeleteSplitCode:
    """Tests for DELETE /api/split-codes/{code} endpoint."""

    def test_delete_existing(self, client_with_db, test_db: Path):
        """Test deleting an existing code."""
        client, db_path = client_with_db

        # Insert a code first
        conn = sqlite3.connect(str(db_path))
        conn.execute("INSERT INTO split_codes (code, split) VALUES ('DEL001', '是')")
        conn.commit()
        conn.close()

        response = client.delete("/api/split-codes/DEL001")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["deleted"] == "DEL001"

    def test_delete_nonexistent(self, client_with_db):
        """Test deleting a non-existent code returns 404."""
        client, _ = client_with_db
        response = client.delete("/api/split-codes/NONEXISTENT")

        assert response.status_code == 404
        assert "未找到" in response.json()["detail"]

    def test_delete_case_insensitive(self, client_with_db, test_db: Path):
        """Test that delete is case-insensitive."""
        client, db_path = client_with_db

        # Insert a code with uppercase
        conn = sqlite3.connect(str(db_path))
        conn.execute("INSERT INTO split_codes (code, split) VALUES ('UPPERCASE', '是')")
        conn.commit()
        conn.close()

        # Delete with lowercase
        response = client.delete("/api/split-codes/uppercase")

        assert response.status_code == 200
        assert response.json()["deleted"] == "uppercase"

    def test_delete_with_path_separator(self, client_with_db, test_db: Path):
        """Test deleting a code that might contain path-like characters."""
        client, db_path = client_with_db

        conn = sqlite3.connect(str(db_path))
        conn.execute("INSERT INTO split_codes (code, split) VALUES ('CODE/SPECIAL', '是')")
        conn.commit()
        conn.close()

        response = client.delete("/api/split-codes/CODE/SPECIAL")

        assert response.status_code == 200


class TestUpdateSplitCode:
    """Tests for PUT /api/split-codes/{old_code} endpoint."""

    def test_update_existing(self, client_with_db, test_db: Path):
        """Test updating an existing code."""
        client, db_path = client_with_db

        conn = sqlite3.connect(str(db_path))
        conn.execute("INSERT INTO split_codes (code, split) VALUES ('UPD001', '是')")
        conn.commit()
        conn.close()

        response = client.put(
            "/api/split-codes/UPD001",
            json={"code": "UPD001_NEW", "split": "否"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["old_code"] == "UPD001"
        assert data["code"] == "UPD001_NEW"
        assert data["split"] == "否"

    def test_update_nonexistent(self, client_with_db):
        """Test updating a non-existent code returns 404."""
        client, _ = client_with_db
        response = client.put(
            "/api/split-codes/NONEXISTENT",
            json={"code": "NEW_CODE", "split": "是"},
        )

        assert response.status_code == 404
        assert "未找到" in response.json()["detail"]

    def test_update_invalid_split(self, client_with_db, test_db: Path):
        """Test updating with invalid split value returns 400."""
        client, db_path = client_with_db

        conn = sqlite3.connect(str(db_path))
        conn.execute("INSERT INTO split_codes (code, split) VALUES ('UPD002', '是')")
        conn.commit()
        conn.close()

        response = client.put(
            "/api/split-codes/UPD002",
            json={"code": "UPD002", "split": "invalid"},
        )

        assert response.status_code == 400
        assert "拆零值必须为「是」或「否」" in response.json()["detail"]

    def test_update_empty_code(self, client_with_db, test_db: Path):
        """Test updating with empty code returns 400."""
        client, db_path = client_with_db

        conn = sqlite3.connect(str(db_path))
        conn.execute("INSERT INTO split_codes (code, split) VALUES ('UPD003', '是')")
        conn.commit()
        conn.close()

        response = client.put(
            "/api/split-codes/UPD003",
            json={"code": "", "split": "是"},
        )

        assert response.status_code == 400
        assert "不能为空" in response.json()["detail"]


class TestBatchUpsertSplitCodes:
    """Tests for PATCH /api/split-codes/batch endpoint."""

    def test_batch_insert(self, client_with_db):
        """Test batch inserting new codes."""
        client, _ = client_with_db
        response = client.patch(
            "/api/split-codes/batch",
            json=[
                {"id": "", "code": "BATCH001", "split": "是"},
                {"id": "", "code": "BATCH002", "split": "否"},
            ],
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["count"] == 2

    def test_batch_update(self, client_with_db, test_db: Path):
        """Test batch updating existing codes."""
        client, db_path = client_with_db

        conn = sqlite3.connect(str(db_path))
        conn.execute("INSERT INTO split_codes (code, split) VALUES ('BATCHUPD001', '是')")
        conn.execute("INSERT INTO split_codes (code, split) VALUES ('BATCHUPD002', '是')")
        conn.commit()
        conn.close()

        response = client.patch(
            "/api/split-codes/batch",
            json=[
                {"id": "BATCHUPD001", "code": "BATCHUPD001", "split": "否"},
                {"id": "BATCHUPD002", "code": "BATCHUPD002_NEW", "split": "否"},
            ],
        )

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 2

    def test_batch_mixed(self, client_with_db, test_db: Path):
        """Test batch with both inserts and updates."""
        client, db_path = client_with_db

        conn = sqlite3.connect(str(db_path))
        conn.execute("INSERT INTO split_codes (code, split) VALUES ('MIXED001', '是')")
        conn.commit()
        conn.close()

        response = client.patch(
            "/api/split-codes/batch",
            json=[
                {"id": "MIXED001", "code": "MIXED001", "split": "否"},  # Update
                {"id": "", "code": "MIXED002", "split": "是"},  # Insert
            ],
        )

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 2

    def test_batch_empty_code_error(self, client_with_db):
        """Test batch with empty code returns error."""
        # Include a valid item first so that INSERT is executed and transaction starts
        client, _ = client_with_db
        response = client.patch(
            "/api/split-codes/batch",
            json=[
                {"id": "", "code": "VALIDFIRST", "split": "是"},  # Valid item to start transaction
                {"id": "", "code": "", "split": "是"},  # Invalid - empty code
            ],
        )

        # Returns 400 with error details
        assert response.status_code == 400
        detail = response.json()["detail"]
        assert isinstance(detail, list)
        assert any("不能为空" in str(e) for e in detail)

    def test_batch_invalid_split_error(self, client_with_db):
        """Test batch with invalid split value returns error."""
        client, _ = client_with_db
        response = client.patch(
            "/api/split-codes/batch",
            json=[
                {"id": "", "code": "VALIDSECOND", "split": "是"},  # Valid item to start transaction
                {"id": "", "code": "INVALIDSPLIT", "split": "maybe"},  # Invalid split value
            ],
        )

        assert response.status_code == 400
        detail = response.json()["detail"]
        assert any("拆零值必须为「是」或「否」" in str(e) for e in detail)

    def test_batch_nonexistent_update_error(self, client_with_db):
        """Test batch update of non-existent code returns error."""
        client, _ = client_with_db
        response = client.patch(
            "/api/split-codes/batch",
            json=[
                {"id": "NONEXISTENT", "code": "NEW_CODE", "split": "是"},
            ],
        )

        assert response.status_code == 400
        detail = response.json()["detail"]
        assert any("未找到" in str(e) for e in detail)

    def test_batch_duplicate_code_error(self, client_with_db, test_db: Path):
        """Test batch with duplicate code returns error."""
        client, db_path = client_with_db

        conn = sqlite3.connect(str(db_path))
        conn.execute("INSERT INTO split_codes (code, split) VALUES ('DUP001', '是')")
        conn.commit()
        conn.close()

        response = client.patch(
            "/api/split-codes/batch",
            json=[
                {"id": "", "code": "DUP001", "split": "否"},  # Duplicate
            ],
        )

        assert response.status_code == 409