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
    "湖南省永州市江华县沱江镇民族路58号（陈玲 徐思思）派乐": "13874605399",
    "湖南省怀化市靖州苗族侗族自治县梅林路中央大街9A栋114.115号门面（石子娴）派乐": "13874407811",
    "湖南省益阳市安化县小淹镇中学对面 （石少青  黄玉平）派乐": "13637411990",
    "湖南省岳阳市岳阳县月田镇（李艳）派乐": "18823858914",
    "湖南省岳阳市岳阳县筻口镇（彭桂华）派乐": "17771626875",
    "湖南省娄底市连源市七星街镇洪源三角坪（欧阳燕青）派乐": "17347592722",
    "湖南省岳阳市华容县东山镇三郎堰居委会（邓枪银）派乐": "18821855511",
    "湖南省怀化市洪江市芙蓉西路飞龙商业广场108-109门面（周宇）派乐": "15274561294",
    "湖南省岳阳市平江县伍市镇（潘云中 李党忠）派乐": "13874007266",
    "湖南省永州市江华瑶族自治县涛圩镇（黄连花）派乐": "13420297524",
    "湖南省郴州市汝城县A区（朱志松）派乐": "18373580888",
    "湖南省怀化市麻阳县腾阳长寿商都1-009 1-010门面（杨小军 杨慧）派乐": "18273862295",
    "湖南省怀化市辰溪县黄溪口镇农贸市场旁（杨小军 蒲彪 张勇）派乐": "18166234208",
    "湖南省怀化市会同县团河镇（曾益兵）派乐": "13874491612",
    "湖南省永州市江华县水口新镇（卿海花）派乐": "17346957687",
    "湖南省永州市零陵区湘口馆路北侧（罗华）派乐": "13627466687",
    "湖南省怀化会同县林城大道金华宾馆(龙思如 梁丽芳)派乐": "18169454768",
    "湖南省永州市江华瑶族自治县马市镇政府门口50米(林友军)派乐": "18975784897",
    "湖南省怀化市鹤城区河西银洲大厦13号门面（杨小军）": "18897487189",
    "湖南省怀化市会同县林城镇山水龙城B3-103 104（向建）派乐": "13874529398",
    "湖南省怀化市洪江市托口镇(邱伟隆)派乐": "15274561294",
    "湖南省岳阳市岳阳县柏祥镇镇西街60号（彭桂华 王诗伟）派乐": "13570843380",
    "湖南省岳阳市岳阳县步仙镇（许辉）派乐": "13575070887",
    "湖南省岳阳市岳阳县黄沙街镇（彭桂华 周大霞）派乐": "18086043035",
    "湖南省岳阳市岳阳县公田镇（彭桂华 姚高钟）派乐": "19998012142",
    "湖南省怀化市锦溪南路346#第一人民医院正大门旁（杨小军）派乐": "18574549950",
    "湖南省汩罗市白水镇湘泉路3号（李春方）派乐": "17759633559",
    "湖南省岳阳市湘阴县南湖洲镇（胡震华）派乐汉堡": "15793986575",
    "湖南省岳阳市平江县瓮江镇（李丹）派乐": "15111728810",
    "湖南省邵阳市城步苗族自治县西岩镇河东新城一栋1号门面（阎光宇）派乐": "18075959975",
    "湖南省长沙市宁乡市花明楼镇安源路428 429号（何芳）派乐": "17788922731",
    "湖南省岳阳市平江县浯口镇（周云云）派乐": "13677164276",
    "湖南省岳阳市平江县上塔市镇（何燎原）派乐": "18711228489",
    "湖南省岳阳市汨罗市长乐镇（黄勇利）派乐": "15576038603",
    "湖南省湘西土家族苗族自治州龙山县民安街道城东路92号（曾祥鹏）派乐": "13135090035",
    "湖南省常德市汉寿县西湖管理区西湖镇人民路101室（李佳豪）派乐": "16673216167",
    "湖南省岳阳市平江县岑川镇（朱波东）派乐": "13874049756",
    "湖南省邵阳市武冈市邓家铺镇（姚家红）派乐": "17873950288",
    "湖南省益阳市桃江县武潭镇（左志刚）派乐": "17707947987",
    "湖南省张家界森林公园乌龙寨停车场（王传明）派乐": "13574418526",
    "湖南省张家界市慈利县三官寺乡新街（杜志刚）派乐": "18974414296",
    "湖南省岳阳市华容县注滋口镇（张明军  彭桂华 ）派乐": "15171161670",
    "湖南省永州市江华县大路铺镇207国道加油站旁（李玉秀）派乐": "18074651320",
    "湖南省怀化市溆浦县桥江镇（彭朝辉 刘军华）派乐": "17872457720",
    "湖南省易俗河（王志辉）派乐": "15200364595",
    "湖南省邵阳市邵阳县长阳铺镇（阳茂）派乐": "15211962779",
    "湖南省益阳市安化县烟溪镇向东路63号（石少青 唐晓剑）派乐": "18074513626",
    "湖南省常德市汉寿县龙阳街道辰阳路恒基公园世家19栋112号店铺（郭稳）派乐": "19329646922",
    "湖南省常德市武陵区西园路1号 一小8号门面（聂长安）派乐": "15073621378",
    "湖南省湘潭市雨湖区新湘路5号(李刚）派乐": "18975439595",
    "湖南省岳阳市平江县龙门镇（李君瑶 ）派乐": "18796615145",
    "湖南省永州市零陵区朝阳街道湖南科技学院松园食堂一楼汉堡铺（龙灿辉）派乐": "18173010481",
    "湖南省娄底市娄星区大埠桥办事处西阳村蒋家组1-A号（高园）派乐": "18973276461",
    "湖南省邵阳县塘渡口镇夫夷天街1005号（张小红）派乐": "15180919066",
    "湖南省怀化鹤城区榆树路274号（杨小军）派乐": "13762950370",
    "湖南省岳阳市临湘市桃林镇（李新龙  柳龙龙）派乐": "15700800255",
    "湖南省永州市新田县新田二中综合楼8号门面（胡晓斌）派乐": "13974625159",
    "湖南省娄底市新化县琅塘镇（欧阳燕青）派乐": "18573857369",
    "湖南省永州市江华县白芒营镇商贸新城万豪甄选生活超市（许斌 何金兰": "18932178756",
    "湖南省岳阳市岳阳县荣家湾（赵永刚）派乐": "13647405500",
    "湖南省怀化市中方县中方镇荆坪社区27栋（梁元 杨小军）派乐": "18608459750",
}


def _seed_pl_customer_phones(conn: sqlite3.Connection) -> None:
    """初始化派乐汉堡客户电话映射。
    数据迁移：如果检测到旧数据是 PHUN 编码格式，先清空再重新 seed（改为客户全文匹配）。
    """
    exists = conn.execute(
        "SELECT COUNT(*) FROM customer_phones WHERE template_key = 'pl'"
    ).fetchone()[0]
    if exists > 0:
        # 检测旧格式（PHUN 编码）：如果有则以新格式重建
        old_fmt = conn.execute(
            "SELECT COUNT(*) FROM customer_phones WHERE template_key = 'pl' AND customer_code LIKE 'PHUN%'"
        ).fetchone()[0]
        if old_fmt > 0:
            conn.execute("DELETE FROM customer_phones WHERE template_key = 'pl'")
        else:
            return  # 已是新格式，不覆盖用户后续的手动修改
    conn.executemany(
        "INSERT OR IGNORE INTO customer_phones (customer_code, phone, template_key) VALUES (?, ?, 'pl')",
        list(_PL_CUSTOMER_PHONES.items()),
    )


def get_customer_phone(customer_code: str, template_key: str = "pl") -> str:
    """按客户（全文地址）查询电话，找不到返回空串"""
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


class CustomerPhoneRepo:
    """客户编码→电话映射 CRUD（门店电话管理）"""
    @staticmethod
    def list(template_key: str = "pl") -> list:
        conn = get_db()
        cur = conn.execute(
            "SELECT customer_code, phone, template_key, created_at FROM customer_phones WHERE template_key = ? ORDER BY created_at DESC",
            (template_key,),
        )
        rows = [
            {"customer_code": row["customer_code"], "phone": row["phone"], "template_key": row["template_key"], "created_at": row["created_at"]}
            for row in cur
        ]
        conn.close()
        return rows

    @staticmethod
    def delete(customer_code: str, template_key: str = "pl") -> bool:
        conn = get_db()
        cur = conn.execute(
            "DELETE FROM customer_phones WHERE LOWER(customer_code) = LOWER(?) AND template_key = ?",
            (customer_code.strip(), template_key),
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
            code = item.get("customer_code", "").strip()
            phone = item.get("phone", "").strip()
            tk = item.get("template_key", "pl")
            item_id = item.get("id", "")
            if not code:
                errors.append({"id": item_id, "error": "客户编码不能为空"})
                continue
            if not phone:
                errors.append({"id": item_id, "error": "电话不能为空"})
                continue
            try:
                if not item_id:
                    conn.execute(
                        "INSERT INTO customer_phones (customer_code, phone, template_key) VALUES (?, ?, ?)",
                        (code, phone, tk),
                    )
                    success.append({"id": item_id or code, "customer_code": code, "phone": phone, "action": "added"})
                else:
                    cur = conn.execute(
                        "UPDATE customer_phones SET customer_code = ?, phone = ? WHERE LOWER(customer_code) = LOWER(?) AND template_key = ?",
                        (code, phone, item_id, tk),
                    )
                    if cur.rowcount == 0:
                        errors.append({"id": item_id, "error": f"未找到客户编码 {item_id}"})
                    else:
                        success.append({"id": item_id, "customer_code": code, "phone": phone, "action": "updated"})
            except _sq.IntegrityError:
                errors.append({"id": item_id, "error": f"客户编码 {code} 已存在"})
        if errors:
            conn.rollback()
            conn.close()
            raise ValueError(errors)
        conn.commit()
        conn.close()
        return {"success": True, "count": len(success), "items": success}