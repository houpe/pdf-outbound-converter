"""
WMS 转换服务 - 日志模块
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

from config import LOG_FILE

LOG_FIELDS = [
    "template_key", "template_name", "file_names", "file_count",
    "item_count", "store_count", "total_quantity", "stores_list",
    "output_filename", "status", "error",
]


def _safe_log(record: Dict[str, Any]) -> None:
    """安全地写入日志条目到 JSONL 文件"""
    entry = {k: record.get(k) for k in LOG_FIELDS if k in record}
    entry["timestamp"] = datetime.now().isoformat()
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        pass