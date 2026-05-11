"""
WMS 转换服务 PDF 解析器
解析黔寨寨 PDF 出库单。
"""

from typing import Dict, List, Tuple

import pdfplumber

from parsers.base import _extract_header_value, _normalize_receiver_name


def extract_pdf_data(pdf_path: str) -> Tuple[Dict[str, str], List[Dict[str, str]]]:
    """打开 PDF 文件，提取文本和表格，解析表头和商品项"""
    with pdfplumber.open(pdf_path) as pdf:
        full_text = ""
        all_tables = []
        for page in pdf.pages:
            full_text += page.extract_text() or ""
            tables = page.extract_tables()
            all_tables.extend(tables)
    return parse_header(full_text), parse_items(all_tables)


def parse_header(text: str) -> Dict[str, str]:
    """使用正则表达式从 PDF 文本中提取表头字段"""
    info = {}
    info["order_no"] = _extract_header_value(text, "单据编号").split()[0] if _extract_header_value(text, "单据编号") else ""
    info["receiver_org"] = _extract_header_value(text, "收货机构")
    info["supplier_org"] = _extract_header_value(text, "供货机构")
    info["receiver_name"] = _normalize_receiver_name(_extract_header_value(text, "收货人"))
    info["receiver_phone"] = _extract_header_value(text, "收货电话")
    info["receiver_address"] = _extract_header_value(text, "收货地址")
    info["order_date"] = _extract_header_value(text, "订单日期").split()[0] if _extract_header_value(text, "订单日期") else ""
    return info


def parse_items(tables: List[List]) -> List[Dict[str, str]]:
    """遍历表格，提取以数字开头的行作为商品项"""
    items = []
    for table in tables:
        for row in table:
            if not row or len(row) < 6:
                continue
            first_cell = str(row[0]).strip()
            if not first_cell.isdigit():
                continue
            item = {
                "category": str(row[1]).strip() if row[1] else "",
                "item_code": str(row[2]).strip() if row[2] else "",
                "item_name": str(row[3]).strip() if row[3] else "",
                "spec": str(row[4]).strip().replace("\n", "") if row[4] else "",
                "unit": str(row[5]).strip() if row[5] else "",
                "quantity": str(row[6]).strip() if row[6] else "0",
                "remark": str(row[7]).strip() if row[7] else "",
            }
            if item["item_code"] and item["item_name"]:
                try:
                    if float(item["quantity"]) <= 0:
                        continue
                except (ValueError, TypeError):
                    pass
                items.append(item)
    return items