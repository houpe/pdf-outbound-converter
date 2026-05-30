import sys
import time
from pathlib import Path

import pytest

backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from middleware.rate_limit import (
    _check_rate_limit, cleanup_rate_limit_store,
    _rate_limit_store, RATE_LIMIT_WINDOW, RATE_LIMIT_MAX,
)


class TestCleanupRateLimitStore:

    def setup_method(self):
        _rate_limit_store.clear()

    def test_no_expired_returns_zero(self):
        now = time.time()
        _rate_limit_store["1.2.3.4"] = [now - 10, now - 5]
        cleaned = cleanup_rate_limit_store(max_age=RATE_LIMIT_WINDOW * 2)
        assert cleaned == 0
        assert "1.2.3.4" in _rate_limit_store

    def test_all_expired_cleared(self):
        old = time.time() - RATE_LIMIT_WINDOW * 3
        _rate_limit_store["1.2.3.4"] = [old, old]
        cleaned = cleanup_rate_limit_store(max_age=RATE_LIMIT_WINDOW * 2)
        assert "1.2.3.4" not in _rate_limit_store

    def test_mixed_keeps_recent(self):
        now = time.time()
        old = now - RATE_LIMIT_WINDOW * 3
        _rate_limit_store["1.2.3.4"] = [old, old, now - 5, now - 1]
        cleanup_rate_limit_store(max_age=RATE_LIMIT_WINDOW * 2)
        assert len(_rate_limit_store["1.2.3.4"]) == 2
        assert all(t > now - RATE_LIMIT_WINDOW * 2 for t in _rate_limit_store["1.2.3.4"])

    def test_default_max_age(self):
        old = time.time() - RATE_LIMIT_WINDOW * 3
        now = time.time()
        _rate_limit_store["5.6.7.8"] = [old, now]
        cleanup_rate_limit_store()
        assert len(_rate_limit_store.get("5.6.7.8", [])) == 1

    def test_custom_max_age(self):
        now = time.time()
        _rate_limit_store["9.10.11.12"] = [now - 50, now - 10]
        cleanup_rate_limit_store(max_age=30)
        assert len(_rate_limit_store.get("9.10.11.12", [])) == 1

    def test_empty_store(self):
        _rate_limit_store.clear()
        result = cleanup_rate_limit_store()
        assert result == 0


class TestRateLimitEdgeCases:

    def setup_method(self):
        _rate_limit_store.clear()

    def test_rapid_sequential_counted(self):
        for _ in range(5):
            _check_rate_limit("10.0.0.1")
        assert len(_rate_limit_store["10.0.0.1"]) == 5

    def test_ip_with_hyphen(self):
        _check_rate_limit("client-proxy-01")
        assert "client-proxy-01" in _rate_limit_store

    def test_ipv6(self):
        _check_rate_limit("2001:db8::1")
        assert "2001:db8::1" in _rate_limit_store

    def test_after_window_expires(self):
        for _ in range(RATE_LIMIT_MAX):
            _check_rate_limit("expire.me")
        old_time = time.time() - RATE_LIMIT_WINDOW - 100
        _rate_limit_store["expire.me"] = [old_time for _ in range(RATE_LIMIT_MAX)]
        _check_rate_limit("expire.me")

    def test_multiple_clients_then_cleanup(self):
        now = time.time()
        _rate_limit_store["a"] = [now]
        _rate_limit_store["b"] = [now - RATE_LIMIT_WINDOW * 3]
        cleanup_rate_limit_store(max_age=RATE_LIMIT_WINDOW * 2)
        assert "a" in _rate_limit_store
        assert "b" not in _rate_limit_store

    def test_hit_limit_cleanup_try_again(self):
        for _ in range(RATE_LIMIT_MAX):
            _check_rate_limit("hit.me")
        with pytest.raises(Exception) as exc:
            _check_rate_limit("hit.me")
        assert exc.value.status_code == 429

        old = time.time() - RATE_LIMIT_WINDOW * 3
        _rate_limit_store["hit.me"] = [old for _ in range(RATE_LIMIT_MAX)]
        cleanup_rate_limit_store(max_age=RATE_LIMIT_WINDOW * 2)
        _check_rate_limit("hit.me")
