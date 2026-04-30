"""
WMS 转换服务配置模块
包含模板定义、路径配置、常量等。
"""

import json
import os
from pathlib import Path

# 基础路径
BASE_DIR = Path(__file__).resolve().parent

# 模板目录：优先查找 backend/templates/（服务器）或 项目根目录的 templates/（本地开发）
ROOT_TEMPLATES = BASE_DIR.parent.parent / "templates"
LOCAL_TEMPLATES = BASE_DIR / "templates"

if LOCAL_TEMPLATES.is_dir():
    TEMPLATES_DIR = LOCAL_TEMPLATES
elif ROOT_TEMPLATES.is_dir():
    TEMPLATES_DIR = ROOT_TEMPLATES
else:
    TEMPLATES_DIR = ROOT_TEMPLATES  # fallback, will fail if neither exists

# 上传和下载目录
UPLOADS_DIR = BASE_DIR / "uploads"
DOWNLOADS_DIR = BASE_DIR / "downloads"
UPLOADS_DIR.mkdir(exist_ok=True)
DOWNLOADS_DIR.mkdir(exist_ok=True)

# 数据库路径
DB_PATH = BASE_DIR / "split_codes.db"

# 日志文件
LOG_FILE = BASE_DIR / "conversion_log.jsonl"


def _find_template(filename: str) -> Path:
    """查找模板文件：优先 templates/ 子目录，回退到 BASE_DIR 同级目录"""
    in_templates = TEMPLATES_DIR / filename
    if in_templates.exists():
        return in_templates
    in_base = BASE_DIR / filename
    if in_base.exists():
        return in_base
    return in_templates  # fallback to original path, will fail if not found


# 模板文件路径
OMS_TEMPLATE = _find_template("OMS出库.xlsx")
SPLIT_TEMPLATE = _find_template("商品拆零模板.xlsx")

# 文件限制
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
MAX_FILE_COUNT = 50

# 下载文件保留时间（秒），默认 24 小时
DOWNLOAD_TTL_SECONDS = 86400

# API 限流：每分钟最多 30 次转换请求
RATE_LIMIT_WINDOW = 60  # 秒
RATE_LIMIT_MAX = 30

# CORS 允许的来源
ALLOWED_ORIGINS = os.environ.get(
    "WMS_CORS_ORIGINS",
    "https://www.houpe.top,http://localhost:5173,http://localhost:3000",
).split(",")

# 表头字段标签
HEADER_FIELD_LABELS = [
    "单据编号", "单据状态", "复审状态", "分拣状态", "是否需要推送", "订单日期",
    "预计发货日期", "期望到货日期", "发货日期", "发货操作时间", "收货机构",
    "订货机构", "供货机构", "送货机构", "业务模式", "配送重量", "收货人",
    "收货电话", "收货地址",
]

import re
HEADER_LABEL_PATTERN = "|".join(re.escape(label) for label in HEADER_FIELD_LABELS)

# 模板定义（默认值，可被 config.json 覆盖）
DEFAULT_TEMPLATES = {
    "qzz": {
        "name": "黔寨寨贵州烙锅",
        "accept": ".pdf",
        "merchant_code": "Q20260427013",
    },
    "lmt": {
        "name": "黎明屯铁锅炖",
        "accept": ".xlsx,.xls",
        "merchant_code": "Q20260427017",
    },
    "hlmc": {
        "name": "欢乐牧场",
        "accept": ".xlsx,.xls",
        "merchant_code": "Q20260427015",
    },
}

# 欢乐牧场默认收件人信息（可通过环境变量 HLMC_RECEIVERS_JSON 或 config.json 覆盖）
DEFAULT_HLMC_RECEIVERS = {
    "银泰": {"name": "王先生", "phone": "15289437124", "address": "湖北省武汉市武昌区银泰创意城欢乐牧场"},
    "金银潭": {"name": "白先生", "phone": "18235064843", "address": "湖北省武汉市东西湖区金银潭永旺欢乐牧场"},
    "金桥": {"name": "张明", "phone": "13382067388", "address": "湖北省武汉市江岸区金桥永旺欢乐牧场"},
}


def _load_config_json() -> dict:
    """尝试加载 config.json 配置文件"""
    config_path = BASE_DIR / "config.json"
    if config_path.exists():
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return {}


def get_templates() -> dict:
    """获取模板配置，优先使用 config.json，否则使用默认值"""
    config = _load_config_json()
    return config.get("templates", DEFAULT_TEMPLATES)


def get_hlmc_receivers() -> dict:
    """获取欢乐牧场收件人信息，优先级：环境变量 > config.json > 默认值"""
    # 1. 环境变量优先
    env_receivers = os.environ.get("HLMC_RECEIVERS_JSON", "")
    if env_receivers:
        try:
            return json.loads(env_receivers)
        except json.JSONDecodeError:
            pass

    # 2. config.json
    config = _load_config_json()
    if "hlmc_receivers" in config:
        return config["hlmc_receivers"]

    # 3. 默认值
    return DEFAULT_HLMC_RECEIVERS


# 导出模板和收件人配置（延迟加载）
TEMPLATES = get_templates()
HLMC_RECEIVERS = get_hlmc_receivers()

# 日志字段
LOG_FIELDS = [
    "template_key", "template_name", "file_names", "file_count",
    "item_count", "store_count", "total_quantity", "stores_list",
    "output_filename", "status", "error",
]