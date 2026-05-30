import json
import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

import importlib
if 'config' in sys.modules:
    del sys.modules['config']

import config


class TestConfigTemplates:

    def test_defaults_exist(self):
        for key in ["qzz", "lmt", "hlmc"]:
            assert key in config.get_templates()

    def test_get_templates_returns_dict(self):
        assert isinstance(config.get_templates(), dict)

    def test_template_structure(self):
        for key, val in config.get_templates().items():
            assert "name" in val
            assert "accept" in val
            assert "merchant_code" in val


class TestConfigHlmcReceivers:

    def test_default_receivers_loaded(self):
        for store in ["银泰", "金银潭", "金桥"]:
            assert store in config.get_hlmc_receivers()

    def test_env_var_override(self, monkeypatch):
        import json as _j
        receivers = {"自定义门店": {"name": "李四", "phone": "139"}}
        monkeypatch.setenv("HLMC_RECEIVERS_JSON", _j.dumps(receivers))

        if 'config' in sys.modules:
            del sys.modules['config']
        import config as _cfg
        assert "自定义门店" in _cfg.HLMC_RECEIVERS

    def test_get_config_json_not_found_returns_default(self, monkeypatch):
        old_base = config.BASE_DIR
        monkeypatch.setattr(config, 'BASE_DIR', Path("/nonexistent"))
        monkeypatch.delenv("HLMC_RECEIVERS_JSON", raising=False)

        if 'config' in sys.modules:
            del sys.modules['config']
        import config as _cfg
        
        assert "银泰" in _cfg.get_hlmc_receivers()


class TestConfigConstants:

    def test_max_file_size(self):
        assert config.MAX_FILE_SIZE == 50 * 1024 * 1024

    def test_max_file_count(self):
        assert config.MAX_FILE_COUNT == 50

    def test_download_ttl(self):
        assert config.DOWNLOAD_TTL_SECONDS == 86400

    def test_rate_limit_window(self):
        assert config.RATE_LIMIT_WINDOW == 60

    def test_rate_limit_max(self):
        assert config.RATE_LIMIT_MAX == 30


class TestConfigPaths:

    def test_base_dir(self):
        assert config.BASE_DIR.is_dir()
        assert "web" in str(config.BASE_DIR) and "backend" in str(config.BASE_DIR)

    def test_dirs_created(self):
        assert config.UPLOADS_DIR.is_dir()
        assert config.DOWNLOADS_DIR.is_dir()
