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


_SPLIT_CODES_SCHEMA = """
    CREATE TABLE split_codes (
        code TEXT NOT NULL,
        split TEXT NOT NULL DEFAULT '是',
        item_name TEXT,
        warehouse_code TEXT NOT NULL DEFAULT 'ZTOWHHY001',
        created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
        UNIQUE(code COLLATE NOCASE, warehouse_code)
    )
"""


def _init_split_codes_table(conn: sqlite3.Connection) -> None:
    table_exists = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='split_codes'"
    ).fetchone()
    old_table_exists = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='_split_codes_old'"
    ).fetchone()

    if old_table_exists and not table_exists:
        conn.execute(_SPLIT_CODES_SCHEMA)
        conn.execute(
            "INSERT INTO split_codes (code, split, item_name, warehouse_code, created_at) "
            "SELECT code, split, item_name, 'ZTOWHHY001', created_at FROM _split_codes_old"
        )
        conn.execute("DROP TABLE _split_codes_old")
        return

    if not table_exists:
        conn.execute(_SPLIT_CODES_SCHEMA)
        return

    cols = [r[1] for r in conn.execute("PRAGMA table_info(split_codes)").fetchall()]
    if 'warehouse_code' in cols:
        return

    conn.execute("ALTER TABLE split_codes RENAME TO _split_codes_old")
    conn.execute(_SPLIT_CODES_SCHEMA)
    conn.execute(
        "INSERT INTO split_codes (code, split, item_name, warehouse_code, created_at) "
        "SELECT code, split, item_name, 'ZTOWHHY001', created_at FROM _split_codes_old"
    )
    conn.execute("DROP TABLE _split_codes_old")


def init_db() -> None:
    """初始化数据库表结构"""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = get_db()
    conn.execute("PRAGMA journal_mode=WAL")

    _init_split_codes_table(conn)

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

    # 客户编码→电话映射表（派乐汉堡等模板用，按客户编码自动匹配收件人电话）
    conn.execute("""
        CREATE TABLE IF NOT EXISTS customer_phones (
            customer_code TEXT NOT NULL,
            phone TEXT NOT NULL,
            template_key TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
            PRIMARY KEY (customer_code, template_key)
        )
    """)

    seed_version_history(conn)
    seed_split_codes(conn)
    seed_default_split_entries(conn)
    _seed_pl_customer_phones(conn)
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
            "INSERT OR IGNORE INTO split_codes (code, split, warehouse_code) VALUES (?, ?, 'ZTOWHHY001')",
            (code, split),
        )
    wb.close()


def seed_default_split_entries(conn: sqlite3.Connection) -> None:
    """Seed 默认拆零配置（ZTOCSYH002 仓库的默认拆零产品）"""
    defaults = [
        ("ZBWP2139", "是"),
        ("ZBWP0185", "是"),
    ]
    for code, split in defaults:
        conn.execute(
            "INSERT OR IGNORE INTO split_codes (code, split, warehouse_code) VALUES (?, ?, 'ZTOCSYH002')",
            (code, split),
        )


VERSION_HISTORY_DATA = [
    {
        "version": "v4.4",
        "date": "2026-05-31 20:00",
        "changes": "拆零管理按仓库隔离（ZTOWHHY001/ZTOCSYH002独立配置）；新增ZTOWHHY001分组（黔寨寨/黎明屯/欢乐牧场）；/wms/无仓库编码时提示联系管理员；ZTOCSYH002新增ZBWP2139/ZBWP0185默认拆零支持",
    },
    {
        "version": "v4.3",
        "date": "2026-05-30 22:00",
        "changes": "新增湖南尹三顺模板（WMS汇总单格式Excel转换）；新增URL分组访问，不同路径显示不同模板，支持可配置扩展；仓库编码ZTOCSYH002，货主编码Q20260526001",
    },
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
    sql_check_seq = "SELECT seq FROM hlmc_sequences WHERE date = ? AND prefix = ?"
    sql_seq_insert = """
        INSERT INTO hlmc_sequences (date, prefix, seq)
        VALUES (?, ?, 1)
        ON CONFLICT(date, prefix) DO NOTHING
    """
    sql_seq_update = """
        UPDATE hlmc_sequences SET seq = seq + 1
        WHERE date = ? AND prefix = ?
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
        
        # 先尝试插入新序列
        conn.execute(sql_seq_insert, (today_str, prefix))
        conn.commit()
        
        # 查询当前序号
        cur = conn.execute(sql_check_seq, (today_str, prefix))
        row = cur.fetchone()
        seq = row["seq"] if row else 1
        
        # 递增
        if seq > 1:
            conn.execute(sql_seq_update, (today_str, prefix))
            conn.commit()
            cur = conn.execute(sql_check_seq, (today_str, prefix))
            row = cur.fetchone()
            seq = row["seq"] if row else 1
        
        order_no = f"{prefix}{today_str}{seq:04d}"
        
        conn.execute(sql_insert_history, (shop_name, today_str, signature, order_no))
        conn.commit()
        return order_no
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def get_split_map(warehouse_code: str = "ZTOWHHY001") -> Dict[str, str]:
    """获取拆零配置映射 {code_lower: split}，按仓库过滤"""
    conn = get_db()
    cur = conn.execute(
        "SELECT code, split FROM split_codes WHERE warehouse_code = ?",
        (warehouse_code,),
    )
    result = {row["code"].lower(): row["split"] for row in cur}
    conn.close()
    return result


# 派乐汉堡客户编码→电话映射（从客户名册 Excel 导入，2026-07-20）
_PL_CUSTOMER_PHONES = {
    "PHUN07461432": "13874605399", "PHUN07457810": "13874407811", "PHUN07396553": "13637411990",
    "PHUN07308299": "18823858914", "PHUN07306382": "17771626875", "PHUN07384969": "17347592722",
    "PXIZ08914568": "18821855511", "PHUN07314894": "15274561294", "PHUN07306868": "13874007266",
    "PHUN07467464": "13420297524", "PHUN07356665": "18373580888", "PHUN07453998": "18273862295",
    "PHUN07455998": "18166234208", "PHUN07459804": "13874491612", "PHUN07461429": "17346957687",
    "PHUN07469828": "13627466687", "PHUN07451419": "18169454768", "PHUN07461430": "18975784897",
    "PHUN07461437": "18897487189", "PHUN07314677": "13874529398", "PHUN07451425": "15274561294",
    "PHUN07306787": "13570843380", "PHUN07307637": "13575070887", "PHUN07307104": "18086043035",
    "PHUN07306617": "19998012142", "PHUN07451417": "18574549950", "PHUN07307217": "17759633559",
    "PHUN07307991": "15793986575", "PHUN07308452": "15111728810", "PHUN07399313": "18075959975",
    "PHUN07318168": "17788922731", "PHUN07306963": "13677164276", "PHUN07309682": "18711228489",
    "PHUN07307153": "15576038603", "PHUN07439872": "13135090035", "PHUN07369357": "16673216167",
    "PHUN07306805": "13874049756", "PHUN07398237": "17873950288", "PHUN07307941": "17707947987",
    "PHUN07446307": "13574418526", "PHUN07441416": "18974414296", "PHUN07307757": "15171161670",
    "PHUN07461431": "18074651320", "PHUN07385075": "17872457720", "PHUN07321404": "15200364595",
    "PHUN07397869": "15211962779", "PHUN07375676": "18074513626", "PHUN07365740": "19329646922",
    "PHUN07368820": "15073621378", "PHUN07328293": "18975439595", "PHUN07307449": "18796615145",
    "PHUN07469607": "18173010481", "PHUN07388990": "18973276461", "PHUN07398193": "15180919066",
    "PHUN07451420": "13762950370", "PHUN07306506": "15700800255", "PHUN07468967": "13974625159",
    "PHUN07386601": "18573857369", "PHUN07461435": "18932178756", "PHUN07306991": "13647405500",
    "PHUN07454649": "18608459750",
}


def _seed_pl_customer_phones(conn: sqlite3.Connection) -> None:
    """初始化派乐汉堡客户电话映射（仅首次创建，不覆盖已有数据）"""
    exists = conn.execute(
        "SELECT COUNT(*) FROM customer_phones WHERE template_key = 'pl'"
    ).fetchone()[0]
    if exists > 0:
        return
    conn.executemany(
        "INSERT OR IGNORE INTO customer_phones (customer_code, phone, template_key) VALUES (?, ?, 'pl')",
        list(_PL_CUSTOMER_PHONES.items()),
    )


def get_customer_phone(customer_code: str, template_key: str = "pl") -> str:
    """按客户编码查询电话，找不到返回空串"""
    if not customer_code:
        return ""
    conn = get_db()
    row = conn.execute(
        "SELECT phone FROM customer_phones WHERE customer_code = ? AND template_key = ?",
        (customer_code.strip(), template_key),
    ).fetchone()
    conn.close()
    return row["phone"] if row else ""


class SplitCodeRepo:
    @staticmethod
    def list(warehouse_code: str = "") -> list:
        conn = get_db()
        if warehouse_code:
            cur = conn.execute(
                "SELECT code, split, item_name, warehouse_code, created_at FROM split_codes WHERE warehouse_code = ? ORDER BY created_at DESC",
                (warehouse_code,),
            )
        else:
            cur = conn.execute("SELECT code, split, item_name, warehouse_code, created_at FROM split_codes ORDER BY created_at DESC")
        codes = [
            {"code": row["code"], "split": row["split"], "item_name": row["item_name"], "warehouse_code": row["warehouse_code"], "created_at": row["created_at"]}
            for row in cur
        ]
        conn.close()
        return codes

    @staticmethod
    def create(code: str, split: str, warehouse_code: str) -> dict:
        import sqlite3 as _sq
        conn = get_db()
        try:
            conn.execute(
                "INSERT INTO split_codes (code, split, warehouse_code) VALUES (?, ?, ?)",
                (code, split, warehouse_code),
            )
            conn.commit()
            return {"success": True, "code": code, "split": split}
        except _sq.IntegrityError:
            raise ValueError(f"商品编码 {code} 在该仓库已存在")
        finally:
            conn.close()

    @staticmethod
    def delete(code: str, warehouse_code: str) -> bool:
        conn = get_db()
        cur = conn.execute(
            "DELETE FROM split_codes WHERE LOWER(code) = LOWER(?) AND warehouse_code = ?",
            (code.strip(), warehouse_code),
        )
        conn.commit()
        conn.close()
        return cur.rowcount > 0

    @staticmethod
    def update(old_code: str, code: str, split: str, warehouse_code: str) -> bool:
        conn = get_db()
        cur = conn.execute(
            "UPDATE split_codes SET code = ?, split = ? WHERE LOWER(code) = LOWER(?) AND warehouse_code = ?",
            (code, split, old_code.strip(), warehouse_code),
        )
        conn.commit()
        conn.close()
        return cur.rowcount > 0

    @staticmethod
    def batch_upsert(items: list) -> dict:
        import sqlite3 as _sq
        conn = get_db()
        success = []
        errors = []
        for item in items:
            code = item.get("code", "").strip()
            split = item.get("split", "")
            wc = item.get("warehouse_code", "ZTOWHHY001")
            item_id = item.get("id", "")
            if not code:
                errors.append({"id": item_id, "error": "编码不能为空"})
                continue
            if split not in ("是", "否"):
                errors.append({"id": item_id, "error": "拆零值必须为「是」或「否」"})
                continue
            try:
                if not item_id:
                    conn.execute(
                        "INSERT INTO split_codes (code, split, warehouse_code, created_at) VALUES (?, ?, ?, datetime('now', 'localtime'))",
                        (code, split, wc),
                    )
                    success.append({"id": item_id or code, "code": code, "split": split, "action": "added"})
                else:
                    cur = conn.execute(
                        "UPDATE split_codes SET code = ?, split = ? WHERE LOWER(code) = LOWER(?) AND warehouse_code = ?",
                        (code, split, item_id, wc),
                    )
                    if cur.rowcount == 0:
                        errors.append({"id": item_id, "error": f"未找到编码 {item_id}"})
                    else:
                        success.append({"id": item_id, "code": code, "split": split, "action": "updated"})
            except _sq.IntegrityError:
                errors.append({"id": item_id, "error": f"商品编码 {code} 在该仓库已存在"})
        if errors:
            conn.rollback()
            conn.close()
            raise ValueError(errors)
        conn.commit()
        conn.close()
        return {"success": True, "count": len(success), "items": success}