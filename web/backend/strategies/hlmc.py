from typing import Any, Dict

from strategies import TemplateStrategy, register_strategy
from parsers.excel_parser_hlmc import parse_hlmc_excel


@register_strategy
class HlmcStrategy(TemplateStrategy):
    key = "hlmc"
    warehouse_code = "ZTOWHHY001"

    def parse(self, path: str, filename: str = ""):
        return parse_hlmc_excel(path)

    def route_quantity(self, quantity, item_code: str, split_map: Dict[str, str]):
        split_flag = split_map.get(item_code.lower(), "")
        if split_flag == "否":
            return ("", quantity)
        return (quantity, "")
