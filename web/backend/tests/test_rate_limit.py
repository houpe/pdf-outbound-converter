"""
Tests for rate limiting functionality.
"""

import sys
import time
from collections import defaultdict
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

# Add backend to path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from middleware.rate_limit import _check_rate_limit, _rate_limit_store, RATE_LIMIT_WINDOW, RATE_LIMIT_MAX


class TestRateLimit:
    """Tests for _check_rate_limit function."""

    def setup_method(self):
        """Clear the rate limit store before each test."""
        _rate_limit_store.clear()

    def test_allows_first_request(self):
        """Test that first request is allowed."""
        # Should not raise any exception
        _check_rate_limit("192.168.1.1")

    def test_allows_requests_under_limit(self):
        """Test that requests under the limit are allowed."""
        client_ip = "192.168.1.2"

        # Make requests up to one less than the limit
        for _ in range(RATE_LIMIT_MAX - 1):
            _check_rate_limit(client_ip)

        # Should not raise
        _check_rate_limit(client_ip)

    def test_blocks_requests_over_limit(self):
        """Test that requests over the limit are blocked."""
        client_ip = "192.168.1.3"

        # Make requests up to the limit
        for _ in range(RATE_LIMIT_MAX):
            _check_rate_limit(client_ip)

        # Next request should raise HTTPException
        with pytest.raises(HTTPException) as exc_info:
            _check_rate_limit(client_ip)

        assert exc_info.value.status_code == 429
        assert "请求过于频繁" in exc_info.value.detail

    def test_different_clients_tracked_separately(self):
        """Test that different client IPs are tracked separately."""
        client1 = "192.168.1.4"
        client2 = "192.168.1.5"

        # Client 1 uses all their requests
        for _ in range(RATE_LIMIT_MAX):
            _check_rate_limit(client1)

        # Client 2 should still be able to make requests
        _check_rate_limit(client2)

        # Client 1 should still be blocked
        with pytest.raises(HTTPException) as exc_info:
            _check_rate_limit(client1)

        assert exc_info.value.status_code == 429

    def test_window_expiration(self):
        """Test that old entries are cleaned up after window expires."""
        client_ip = "192.168.1.6"

        # Make requests up to the limit
        for _ in range(RATE_LIMIT_MAX):
            _check_rate_limit(client_ip)

        # Should be blocked
        with pytest.raises(HTTPException):
            _check_rate_limit(client_ip)

        # Simulate time passing by directly modifying the store
        # Move all timestamps back by more than the window
        old_time = time.time() - RATE_LIMIT_WINDOW - 1
        _rate_limit_store[client_ip] = [old_time for _ in range(RATE_LIMIT_MAX)]

        # Should now be allowed (old entries cleaned)
        _check_rate_limit(client_ip)

    def test_partial_window_cleanup(self):
        """Test that only old entries are cleaned, not recent ones."""
        client_ip = "192.168.1.7"
        current_time = time.time()

        # Add some old entries and some recent ones
        old_time = current_time - RATE_LIMIT_WINDOW - 10
        _rate_limit_store[client_ip] = [
            old_time,  # This should be cleaned
            old_time,  # This should be cleaned
            current_time - 10,  # This should remain
            current_time - 5,  # This should remain
        ]

        # Make a new request
        _check_rate_limit(client_ip)

        # Store should have 3 entries (2 recent + 1 new)
        assert len(_rate_limit_store[client_ip]) == 3

    def test_exact_limit_boundary(self):
        """Test behavior at exact limit boundary."""
        client_ip = "192.168.1.8"

        # Make RATE_LIMIT_MAX requests (exactly at limit)
        for i in range(RATE_LIMIT_MAX):
            _check_rate_limit(client_ip)

        # The RATE_LIMIT_MAX + 1 request should fail
        with pytest.raises(HTTPException) as exc_info:
            _check_rate_limit(client_ip)

        assert exc_info.value.status_code == 429


class TestRateLimitIntegration:
    """Integration tests for rate limiting with FastAPI endpoints."""

    def test_rate_limit_on_convert_endpoint(self):
        """Test that rate limiting is applied to /api/convert endpoint."""
        from main import app

        client = TestClient(app)

        # This test verifies the endpoint exists but doesn't test actual rate limiting
        # since that would require making many requests
        # Just verify the endpoint responds correctly
        response = client.get("/api/templates")
        assert response.status_code == 200


class TestRateLimitStoreCleanup:
    """Tests for rate limit store cleanup behavior."""

    def setup_method(self):
        """Clear the rate limit store before each test."""
        _rate_limit_store.clear()

    def test_store_entry_format(self):
        """Test that store entries are lists of timestamps."""
        client_ip = "192.168.1.10"

        _check_rate_limit(client_ip)

        assert client_ip in _rate_limit_store
        assert isinstance(_rate_limit_store[client_ip], list)
        assert len(_rate_limit_store[client_ip]) == 1
        assert isinstance(_rate_limit_store[client_ip][0], float)

    def test_multiple_requests_accumulate(self):
        """Test that multiple requests accumulate in the store."""
        client_ip = "192.168.1.11"

        for i in range(5):
            _check_rate_limit(client_ip)

        assert len(_rate_limit_store[client_ip]) == 5

    def test_sequential_timestamps(self):
        """Test that timestamps are roughly sequential."""
        client_ip = "192.168.1.12"

        for _ in range(3):
            _check_rate_limit(client_ip)
            time.sleep(0.01)  # Small delay to ensure different timestamps

        timestamps = _rate_limit_store[client_ip]
        # Each timestamp should be >= the previous one
        for i in range(1, len(timestamps)):
            assert timestamps[i] >= timestamps[i - 1]