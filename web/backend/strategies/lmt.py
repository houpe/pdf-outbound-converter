from typing import Any, Dict, List

from fastapi import HTTPException

from strategies import TemplateStrategy, register_strategy
from parsers.excel_parser_lmt import parse_lmt_excel


@register_strategy
class LmtStrategy(TemplateStrategy):
    key = "lmt"
    warehouse_code = "ZTOWHHY001"
    validate_split_codes = True

    def parse(self, path: str, filename: str = ""):
        return parse_lmt_excel(path, filename)

    def route_quantity(self, quantity, item_code: str, split_map: Dict[str, str]):
        split_flag = split_map.get(item_code.lower(), "")
        if split_flag == "否":
            return ("", quantity)
        return (quantity, "")

    def validate_items(self, items: List[Dict[str, str]], split_map: Dict[str, str]) -> None:
        missing_items: List[Dict[str, str]] = []
        for item in items:
            ic = str(item["item_code"]).strip()
            if ic and ic.lower() not in split_map:
                sf = item.get("source_file", "未知文件")
                name = item.get("item_name", "—")
                missing_items.append({"code": ic, "name": name, "source": sf})
        seen: set = set()
        unique_missing: List[Dict[str, str]] = []
        for m in missing_items:
            if m["code"] not in seen:
                seen.add(m["code"])
                unique_missing.append(m)
        if unique_missing:
            msg_parts = [f"「{m['code']}」（来自 {m['source']}）" for m in unique_missing]
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "商品编码缺失",
                    "codes": unique_missing,
                    "message": f"以下 {len(unique_missing)} 个商品编码不在拆零管理表中：\n" + "\n".join(msg_parts)
                }
            )
