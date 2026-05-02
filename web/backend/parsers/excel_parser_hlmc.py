"""
WMS 转换服务 Excel 解析器 - 欢乐牧场
解析欢乐牧场 Excel 出库单。
"""

from datetime import date
from typing import Dict, List, Tuple
import uuid

import openpyxl

from config import HLMC_RECEIVERS


def parse_hlmc_excel(excel_path: str) -> Tuple[Dict[str, str], List[Dict[str, str]]]:
    wb = openpyxl.load_workbook(excel_path, data_only=True)
    ws = wb.active
    all_records: List[Dict[str, str]] = []

    # 生成日期订单号: YYMMDD + 4位随机数 (Business Requirement)
    today_str = date.today().strftime("%y%m%d")
    random_suffix = f"{uuid.uuid4().int % 10000:04d}"
    generated_order_no = f"{today_str}{random_suffix}"

    header_row = ws[1]
    col_frozen = None
    col_unit = None
    col_surplus = None
    col_sku_name = None
    col_ext_code = None
    col_sku_unit = None
    col_sku_spec = None

    for c in range(1, ws.max_column + 1):
        val = str(header_row[c - 1].value or "").strip()
        if val == "冻结数量的总和":
            col_frozen = c
        elif val == "单位":
            col_unit = c
        elif val == "下单后结余":
            col_surplus = c
        elif val in ("SKU名称", "商品名称"):
            col_sku_name = c
        elif val == "外部商品编码":
            col_ext_code = c
        elif val == "商品编码" and not col_ext_code:
            col_ext_code = c
        elif val in ("库存单位", "单位"):
            col_sku_unit = c
        elif val == "规格":
            col_sku_spec = c

    if col_surplus is None:
        raise ValueError("欢乐牧场模板格式错误：找不到\"下单后结余\"列")

    shop_start = col_frozen if col_frozen else (col_unit if col_unit else 0)

    shop_cols: Dict[int, str] = {}
    for c in range(shop_start + 1, col_surplus):
        shop_name = str(header_row[c - 1].value or "").strip()
        if shop_name:
            shop_cols[c] = shop_name

    if not shop_cols:
        for c in range(1, col_surplus):
            v = header_row[c - 1].value
            if v and str(v).strip():
                shop_cols[c] = str(v).strip()

    if not shop_cols:
        raise ValueError("欢乐牧场模板格式错误：找不到店铺列")

    def _match_store(shop_name: str) -> Dict[str, str]:
        for key, recv in HLMC_RECEIVERS.items():
            if key in shop_name:
                return recv
        return {}

    r = 2
    while r <= ws.max_row:
        sku_name = ws.cell(row=r, column=col_sku_name).value if col_sku_name else ""
        ext_code = ws.cell(row=r, column=col_ext_code).value if col_ext_code else ""

        if not sku_name and not ext_code:
            r += 1
            continue

        sku_unit = str(ws.cell(row=r, column=col_unit).value or "").strip() if col_unit else ""
        sku_spec = str(ws.cell(row=r, column=col_sku_spec).value or "").strip() if col_sku_spec else ""

        for col_idx, shop_name in shop_cols.items():
            qty = ws.cell(row=r, column=col_idx).value
            if qty is not None:
                try:
                    qty_val = float(qty)
                except (ValueError, TypeError):
                    qty_val = 0
                if qty_val > 0:
                    recv = _match_store(shop_name)
                    all_records.append({
                        "item_code": str(ext_code or "").strip(),
                        "item_name": str(sku_name or "").strip(),
                        "quantity": str(int(float(qty))),
                        "unit": sku_unit,
                        "spec": sku_spec,
                        "category": "",
                        "remark": "",
                        "receiver_org": shop_name,
                        "receiver_name": recv.get("name", ""),
                        "receiver_phone": recv.get("phone", ""),
                        "receiver_address": recv.get("address", ""),
                        "order_no": generated_order_no,
                        "supplier_org": "",
                        "order_date": "",
                    })
        r += 1

    info = {
        "order_no": generated_order_no,
        "receiver_org": "",
        "supplier_org": "",
        "receiver_name": "",
        "receiver_phone": "",
        "receiver_address": "",
        "order_date": "",
    }
    return info, all_records
