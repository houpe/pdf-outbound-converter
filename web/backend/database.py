"""
WMS 转换服务数据库模块
包含 SQLite 数据库连接、初始化、拆零配置管理。
"""

import sqlite3
from pathlib import Path
from typing import Dict

import openpyxl

from config import DB_PATH, SPLIT_TEMPLATE

# 模块级连接缓存
_connection_cache: dict = {}


def get_db() -> sqlite3.Connection:
    """获取数据库连接，使用 Row 工厂和 WAL 模式"""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db() -> None:
    """初始化数据库表结构"""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS split_codes (
            code TEXT PRIMARY KEY COLLATE NOCASE,
            split TEXT NOT NULL DEFAULT '是',
            item_name TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
        )
    """)

    # 检查并添加新列
    cols = [r[1] for r in conn.execute("PRAGMA table_info(split_codes)")]
    if 'created_at' not in cols:
        try:
            conn.execute("ALTER TABLE split_codes ADD COLUMN created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))")
        except sqlite3.OperationalError:
            pass
    if 'item_name' not in cols:
        try:
            conn.execute("ALTER TABLE split_codes ADD COLUMN item_name TEXT")
        except sqlite3.OperationalError:
            pass

    seed_split_codes(conn)
    conn.commit()
    conn.close()


def seed_split_codes(conn: sqlite3.Connection) -> None:
    """从商品拆零模板.xlsx 导入拆零规则，不覆盖已有配置"""
    if not SPLIT_TEMPLATE.exists():
        return

    wb = openpyxl.load_workbook(SPLIT_TEMPLATE, data_only=True, read_only=True)
    ws = wb.active
    rows = ws.iter_rows(values_only=True)
    header = next(rows, None)
    if not header:
        wb.close()
        return

    labels = [str(v or "").strip() for v in header]
    try:
        code_idx = labels.index("商品编码")
        split_idx = labels.index("是否拆零")
    except ValueError:
        wb.close()
        return

    for row in rows:
        if not row or len(row) <= max(code_idx, split_idx):
            continue
        code = str(row[code_idx] or "").strip()
        split = str(row[split_idx] or "是").strip()
        if not code:
            continue
        if split not in ("是", "否"):
            split = "是"
        conn.execute(
            "INSERT OR IGNORE INTO split_codes (code, split) VALUES (?, ?)",
            (code, split),
        )
    wb.close()


def get_split_map() -> Dict[str, str]:
    """获取拆零配置映射 {code_lower: split}"""
    conn = get_db()
    cur = conn.execute("SELECT code, split FROM split_codes")
    result = {row["code"].lower(): row["split"] for row in cur}
    conn.close()
    return result