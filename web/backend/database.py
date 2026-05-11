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
    conn.execute("""
        CREATE TABLE IF NOT EXISTS hlmc_sequences (
            date TEXT NOT NULL,
            prefix TEXT NOT NULL,
            seq INTEGER NOT NULL DEFAULT 1,
            PRIMARY KEY (date, prefix)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS hlmc_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            shop_name TEXT,
            date TEXT NOT NULL,
            signature TEXT NOT NULL UNIQUE,
            order_no TEXT NOT NULL
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_hlmc_hist_sig ON hlmc_history(signature)")

    conn.execute("""
        CREATE TABLE IF NOT EXISTS version_history (
            version TEXT PRIMARY KEY,
            date TEXT NOT NULL,
            changes TEXT NOT NULL
        )
    """)

    seed_version_history(conn)

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


VERSION_HISTORY_DATA = [
    {
        "version": "v4.2",
        "date": "2026-05-11 13:23",
        "changes": "三家模板统一优化：商品数量为 0 或负数时自动排除，不进入转换结果",
    },
    {
        "version": "v4.1",
        "date": "2026-05-10 00:00",
        "changes": "三家模板收件人姓名优化：单字姓名自动重复为双字（如\"张\"→\"张张\"）",
    },
    {
        "version": "v4.0",
        "date": "2026-05-07 00:00",
        "changes": "黎明屯铁锅炖模板：收件人电话统一固定为 18888888888；新增 190+ pytest 测试套件覆盖全模块；前端架构重构：组件化拆分 + lib 模块统一管理",
    },
    {
        "version": "v3.9",
        "date": "2025-05-02 12:00",
        "changes": "欢乐牧场模板：订单号重构，采用 YYMMDD + 4位随机数 (如 2605020001)；优化多文件累加选择逻辑，支持自动去重合并；新增‘清除全部’按钮，单文件状态亦可使用",
    },
    {
        "version": "v3.8",
        "date": "2025-05-02 02:00",
        "changes": "前端架构重构：App.jsx 精简为 13 行路由控制器，核心逻辑拆解至 features/convert；新增组件化库：提取 Button/Badge/Card/Modal/Toast 等通用 UI 组件；UI 升级：转换页升级为双栏工作台布局，集成 Toast 通知和自动下载容错；新增 lib 模块：统一管理 API 请求 (apiClient) 和错误处理 (errors)",
    },
    {
        "version": "v3.7",
        "date": "2025-05-01 22:30",
        "changes": "首页增加版本号徽章，点击即可查看完整更新记录弹窗；修复欢乐牧场模板中无商品编码/名称的行被错误转换的问题",
    },
    {
        "version": "v3.6",
        "date": "2026-04-29 18:58",
        "changes": "后端模块化重构：拆分单文件为 config/database/schemas/parsers/services/middleware；前端提取共享 Icons/SplitToggle 组件，内联样式迁移到 CSS；新增 70+ pytest 测试套件覆盖解析/转换/CRUD/限流；启用 API 限流，收紧 CORS 策略",
    },
    {
        "version": "v3.5",
        "date": "2025-05-01 12:00",
        "changes": "商品拆零配置改为 SQLite 页面维护；拆零管理支持内联新增/编辑/保存、创建时间倒序、页面内确认删除；黎明屯缺失编码支持弹窗内配置并重试；仅黎明屯转换校验拆零配置",
    },
    {
        "version": "v3.4",
        "date": "2025-04-28 16:54",
        "changes": "修复拆零路由：新增模板回退查找逻辑；LMT门店信息从模板「收货机构」读取",
    },
    {
        "version": "v3.3",
        "date": "2025-04-28 12:00",
        "changes": "新增转换日志（JSONL）、拆零模板自动路由；转换成功后自动下载",
    },
    {
        "version": "v3.2",
        "date": "2025-04-28 10:00",
        "changes": "安全加固：路径遍历防护、lifespan 替换废弃 API；清理端点移除、requirements 合并",
    },
    {
        "version": "v3.1",
        "date": "2025-04-27 18:00",
        "changes": "CORS 限定来源、动态模板获取；流式上传、TTL 清理、文件限制",
    },
    {
        "version": "v3.0",
        "date": "2025-04-27 14:00",
        "changes": "重构为Web应用（FastAPI + React），删除桌面端代码",
    },
    {
        "version": "v2.3",
        "date": "2025-04-25 10:00",
        "changes": "重构项目目录 (src/assets/templates)，欢乐牧场合并输出",
    },
    {
        "version": "v2.2",
        "date": "2025-04-24 16:00",
        "changes": "新增欢乐牧场模板",
    },
    {
        "version": "v2.1",
        "date": "2025-04-24 10:00",
        "changes": "新增黎明屯铁锅炖模板",
    },
    {
        "version": "v2.0",
        "date": "2025-04-23 15:00",
        "changes": "多模板下拉选择器",
    },
    {
        "version": "v1.3",
        "date": "2025-04-20 10:00",
        "changes": "优化异步处理和日志显示",
    },
    {
        "version": "v1.2",
        "date": "2025-04-18 12:00",
        "changes": "双平台打包支持",
    },
    {
        "version": "v1.1",
        "date": "2025-04-15 09:00",
        "changes": "GUI界面",
    },
    {
        "version": "v1.0",
        "date": "2025-04-10 08:00",
        "changes": "基础PDF转Excel",
    },
]


def seed_version_history(conn: sqlite3.Connection) -> None:
    """将版本历史记录写入数据库，不覆盖已有配置"""
    for entry in VERSION_HISTORY_DATA:
        conn.execute(
            "INSERT OR IGNORE INTO version_history (version, date, changes) VALUES (?, ?, ?)",
            (entry["version"], entry["date"], entry["changes"]),
        )


def get_hlmc_order(shop_name: str, today_str: str, signature: str, prefix: str) -> str:
    sql_history = "SELECT order_no FROM hlmc_history WHERE signature = ?"
    sql_seq_update = """
        INSERT INTO hlmc_sequences (date, prefix, seq)
        VALUES (?, ?, 1)
        ON CONFLICT(date, prefix) DO UPDATE SET seq = seq + 1
        RETURNING seq
    """
    sql_insert_history = """
        INSERT INTO hlmc_history (shop_name, date, signature, order_no)
        VALUES (?, ?, ?, ?)
    """
    
    conn = get_db()
    try:
        cur = conn.execute(sql_history, (signature,))
        row = cur.fetchone()
        if row:
            return row["order_no"]

        cur = conn.execute(sql_seq_update, (today_str, prefix))
        row = cur.fetchone()
        new_seq = row["seq"]
        new_order = f"{prefix}{today_str}{new_seq:04d}"

        conn.execute(sql_insert_history, (shop_name, today_str, signature, new_order))
        conn.commit()
        return new_order
    finally:
        conn.close()


def get_split_map() -> Dict[str, str]:
    """获取拆零配置映射 {code_lower: split}"""
    conn = get_db()
    cur = conn.execute("SELECT code, split FROM split_codes")
    result = {row["code"].lower(): row["split"] for row in cur}
    conn.close()
    return result