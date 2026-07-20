"""
派乐汉堡模板策略。
- 仓库：长沙雨花二仓 ZTOCSYH002
- 实发数量固定路由到 I 列（一级/二级单位），不按拆零配置分流
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
        # 实发数量统一放 I 列（一级/二级单位），不管拆零配置
        return (quantity, "")
