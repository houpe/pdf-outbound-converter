"""
WMS 转换服务 - 限流中间件
"""

import time
from collections import defaultdict
from typing import Dict, List

from fastapi import HTTPException

from config import RATE_LIMIT_WINDOW, RATE_LIMIT_MAX

# 限流存储
_rate_limit_store: Dict[str, List[float]] = defaultdict(list)


def _check_rate_limit(client_ip: str) -> None:
    """检查客户端请求频率，超限则抛出 429 异常"""
    now = time.time()
    window_start = now - RATE_LIMIT_WINDOW
    _rate_limit_store[client_ip] = [
        t for t in _rate_limit_store[client_ip] if t > window_start
    ]
    if len(_rate_limit_store[client_ip]) >= RATE_LIMIT_MAX:
        raise HTTPException(status_code=429, detail="请求过于频繁，请稍后再试")
    _rate_limit_store[client_ip].append(now)


def cleanup_rate_limit_store(max_age: float = None) -> int:
    """清理过期的限流记录，返回清理数量"""
    if max_age is None:
        max_age = RATE_LIMIT_WINDOW * 2
    now = time.time()
    cutoff = now - max_age
    cleaned = 0
    for ip in list(_rate_limit_store.keys()):
        original_len = len(_rate_limit_store[ip])
        _rate_limit_store[ip] = [t for t in _rate_limit_store[ip] if t > cutoff]
        if not _rate_limit_store[ip]:
            del _rate_limit_store[ip]
        else:
            cleaned += original_len - len(_rate_limit_store[ip])
    return cleaned