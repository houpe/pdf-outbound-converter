import json
import sys
from pathlib import Path

import pytest

backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from services.logging_svc import _safe_log, LOG_FIELDS


class TestSafeLog:

    def test_writes_jsonl(self, tmp_path, monkeypatch):
        log_file = tmp_path / "test_log.jsonl"
        monkeypatch.setattr("services.logging_svc.LOG_FILE", log_file)

        _safe_log({"template_key": "qzz", "status": "success", "item_count": 3})

        lines = log_file.read_text().strip().split("\n")
        assert len(lines) == 1
        entry = json.loads(lines[0])
        assert entry["template_key"] == "qzz"
        assert entry["status"] == "success"
        assert entry["item_count"] == 3
        assert "timestamp" in entry

    def test_filters_to_known_fields(self, tmp_path, monkeypatch):
        log_file = tmp_path / "filtered.jsonl"
        monkeypatch.setattr("services.logging_svc.LOG_FILE", log_file)

        _safe_log({
            "template_key": "lmt",
            "unknown_field": "should be dropped",
            "status": "fail",
        })

        entry = json.loads(log_file.read_text().strip())
        assert "template_key" in entry
        assert entry["template_key"] == "lmt"
        assert "unknown_field" not in entry

    def test_handles_file_error_silently(self, monkeypatch, tmp_path):
        invalid_path = tmp_path / "nonexistent" / "log.jsonl"
        monkeypatch.setattr("services.logging_svc.LOG_FILE", invalid_path)

        try:
            _safe_log({"template_key": "test"})
        except Exception:
            pytest.fail("Should handle error silently")


class TestLogFields:

    def test_expected_fields_present(self):
        assert "template_key" in LOG_FIELDS
        assert "template_name" in LOG_FIELDS
        assert "file_count" in LOG_FIELDS
        assert "item_count" in LOG_FIELDS
        assert "status" in LOG_FIELDS
        assert "error" in LOG_FIELDS
