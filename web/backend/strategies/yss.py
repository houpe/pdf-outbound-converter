from typing import Any, Dict

from strategies import TemplateStrategy, register_strategy
from parsers.excel_parser_yss import parse_yss_excel


@register_strategy
class YssStrategy(TemplateStrategy):
    key = "yss"
    warehouse_code = "ZTOCSYH002"

    def parse(self, path: str, filename: str = ""):
        return parse_yss_excel(path)

    def route_quantity(self, quantity, item_code: str, split_map: Dict[str, str]):
        split_flag = split_map.get(item_code.lower(), "")
        if split_flag == "是":
            return (quantity, "")
        return ("", quantity)
