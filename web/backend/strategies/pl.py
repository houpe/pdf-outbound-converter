"""
派乐汉堡模板策略。
- 仓库：长沙雨花二仓 ZTOCSYH002
- 实发数量固定路由到 J 列（最小单位数量），因为库存单位是件/袋/条等最小销售单位
"""

from typing import Any, Dict, Tuple

from strategies import TemplateStrategy, register_strategy
from parsers.excel_parser_pl import parse_pl_excel


@register_strategy
class PlStrategy(TemplateStrategy):
    key = "pl"
    warehouse_code = "ZTOCSYH002"
    validate_split_codes = False

    def parse(self, path: str, filename: str = ""):
        return parse_pl_excel(path)

    def route_quantity(self, quantity, item_code: str, split_map: Dict[str, str]) -> Tuple[Any, Any]:
        # 库存单位是件/袋/条等最小销售单位 → 实发数量放 J 列（最小单位数量）
        return ("", quantity)
