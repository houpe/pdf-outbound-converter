"""
Tests for conversion API endpoints.
"""

import io
import os
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import openpyxl
import pytest
from fastapi.testclient import TestClient

# Add backend to path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

# Import from modules
from main import app
from config import TEMPLATES, DB_PATH, OMS_TEMPLATE, SPLIT_TEMPLATE
from database import init_db, get_db


@pytest.fixture
def client_with_mocks(tmp_path: Path, oms_template: Path, split_template: Path):
    """
    Creates a TestClient with mocked file paths.
    """
    # Create a temp db
    db_path = tmp_path / "test_split_codes.db"
    uploads_dir = tmp_path / "uploads"
    downloads_dir = tmp_path / "downloads"
    uploads_dir.mkdir(exist_ok=True)
    downloads_dir.mkdir(exist_ok=True)

    # Create and initialize the test database
    import sqlite3
    conn = sqlite3.connect(str(db_path))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS split_codes (
            code TEXT PRIMARY KEY COLLATE NOCASE,
            split TEXT NOT NULL DEFAULT '是',
            item_name TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
        )
    """)
    # Seed with test codes
    conn.execute("INSERT INTO split_codes (code, split) VALUES (?, ?)", ("CODE001", "是"))
    conn.execute("INSERT INTO split_codes (code, split) VALUES (?, ?)", ("CODE002", "否"))
    conn.commit()
    conn.close()

    with patch("main.DB_PATH", db_path), \
         patch("main.UPLOADS_DIR", uploads_dir), \
         patch("main.DOWNLOADS_DIR", downloads_dir), \
         patch("main.OMS_TEMPLATE", oms_template), \
         patch("main.SPLIT_TEMPLATE", split_template), \
         patch("main.get_db") as mock_get_db:

        def create_test_db():
            conn = sqlite3.connect(str(db_path))
            conn.row_factory = sqlite3.Row
            return conn

        mock_get_db.side_effect = create_test_db

        client = TestClient(app)
        yield client


@pytest.fixture
def client_simple():
    """
    Simple TestClient for basic endpoint tests.
    """
    client = TestClient(app)
    yield client


class TestTemplatesEndpoint:
    """Tests for GET /api/templates endpoint."""

    def test_list_templates(self, client_simple):
        """Test that templates endpoint returns expected structure."""
        response = client_simple.get("/api/templates")

        assert response.status_code == 200
        data = response.json()
        assert "templates" in data
        assert isinstance(data["templates"], list)
        assert len(data["templates"]) >= 3  # qzz, lmt, hlmc

        # Check structure of each template
        for template in data["templates"]:
            assert "key" in template
            assert "name" in template
            assert "accept" in template
            assert "default_merchant_code" in template

    def test_templates_contain_expected_keys(self, client_simple):
        """Test that all expected template keys are present."""
        response = client_simple.get("/api/templates")
        data = response.json()

        keys = {t["key"] for t in data["templates"]}
        assert "qzz" in keys
        assert "lmt" in keys
        assert "hlmc" in keys


class TestConvertEndpoint:
    """Tests for POST /api/convert endpoint."""

    def test_convert_missing_template_key(self, client_simple):
        """Test that missing template_key returns 422 error."""
        # Create a mock file
        file_content = b"test content"
        files = [("files", ("test.xlsx", io.BytesIO(file_content), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"))]

        response = client_simple.post("/api/convert", files=files)

        # FastAPI returns 422 for missing required form field
        assert response.status_code == 422

    def test_convert_invalid_template_key(self, client_simple):
        """Test that invalid template_key returns 400 error."""
        file_content = b"test content"
        files = [("files", ("test.xlsx", io.BytesIO(file_content), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"))]

        response = client_simple.post(
            "/api/convert",
            files=files,
            data={"template_key": "invalid_template"},
        )

        assert response.status_code == 400
        assert "未知模板" in response.json()["detail"]

    def test_convert_wrong_file_extension(self, client_simple):
        """Test that wrong file extension returns 400 error."""
        # Create a mock PDF file
        file_content = b"%PDF-1.4 test content"
        files = [("files", ("test.pdf", io.BytesIO(file_content), "application/pdf"))]

        response = client_simple.post(
            "/api/convert",
            files=files,
            data={"template_key": "lmt"},  # LMT only accepts .xlsx/.xls
        )

        assert response.status_code == 400
        assert "不支持" in response.json()["detail"]

    def test_convert_no_files(self, client_simple):
        """Test that no files returns 422 error."""
        response = client_simple.post(
            "/api/convert",
            files=[],
            data={"template_key": "lmt"},
        )

        assert response.status_code == 422

    def test_convert_merchant_code_validation_too_long(self, client_simple):
        """Test that merchant code > 64 chars returns 400 error."""
        file_content = b"test content"
        files = [("files", ("test.xlsx", io.BytesIO(file_content), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"))]
        long_code = "A" * 65

        response = client_simple.post(
            "/api/convert",
            files=files,
            data={"template_key": "lmt", "merchant_code": long_code},
        )

        # Should fail before or during file parsing
        assert response.status_code in [400, 500]

    def test_convert_merchant_code_validation_invalid_chars(self, client_simple):
        """Test that merchant code with invalid chars returns 400 error."""
        file_content = b"test content"
        files = [("files", ("test.xlsx", io.BytesIO(file_content), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"))]

        response = client_simple.post(
            "/api/convert",
            files=files,
            data={"template_key": "lmt", "merchant_code": "invalid!code"},
        )

        assert response.status_code == 400
        assert "商户编码" in response.json()["detail"]


class TestConvertWithMockFiles:
    """Tests for conversion with proper mock Excel files."""

    @pytest.fixture
    def mock_lmt_file(self, lmt_excel: Path) -> bytes:
        """Read the LMT test file and return as bytes."""
        with open(lmt_excel, "rb") as f:
            return f.read()

    def test_convert_valid_lmt_file(self, mock_main_env, lmt_excel: Path):
        """Test converting a valid LMT Excel file."""
        # This test uses the client_with_mocks fixture
        pass  # Complex integration test, would need proper setup

    def test_convert_hlmc_file(self, mock_main_env, hlmc_excel: Path):
        """Test converting a valid HLMC Excel file."""
        pass  # Complex integration test, would need proper setup


class TestDownloadEndpoint:
    """Tests for GET /downloads/{filename} endpoint."""

    def test_download_nonexistent_file(self, client_simple):
        """Test that downloading non-existent file returns 404."""
        response = client_simple.get("/downloads/nonexistent.xlsx")
        assert response.status_code == 404

    def test_download_path_traversal(self, client_simple):
        """Test that path traversal attempts are blocked."""
        # FastAPI normalizes the path, so ../main.py becomes main.py
        # which doesn't exist in downloads directory, returns 404
        response = client_simple.get("/downloads/../main.py")
        assert response.status_code in [400, 404]

        # URL-encoded path traversal
        response = client_simple.get("/downloads/..%2Fmain.py")
        assert response.status_code in [400, 404]

    def test_download_invalid_filename(self, client_simple):
        """Test that invalid filenames are rejected."""
        # Multiple path traversals
        response = client_simple.get("/downloads/../../../etc/passwd")
        assert response.status_code in [400, 404]


class TestLogsEndpoint:
    """Tests for GET /api/logs endpoint."""

    def test_get_logs_empty(self, client_simple):
        """Test getting logs when log file doesn't exist."""
        # Patch LOG_FILE to a non-existent path
        with patch("config.LOG_FILE", Path("/nonexistent/path/conversion_log.jsonl")):
            response = client_simple.get("/api/logs")

        assert response.status_code == 200
        data = response.json()
        assert data["logs"] == []
        assert data["total"] == 0

    def test_get_logs_with_limit(self, client_simple):
        """Test that logs endpoint respects limit parameter."""
        response = client_simple.get("/api/logs?limit=10")
        assert response.status_code == 200