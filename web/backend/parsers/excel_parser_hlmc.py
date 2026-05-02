"""
WMS 转换服务 Excel 解析器 - 欢乐牧场
解析欢乐牧场 Excel 出库单。
"""

import json
import os
import threading
from datetime import date
from typing import Dict, List, Tuple

import openpyxl

from config import HLMC_RECEIVERS

SHOP_ABBREVIATIONS = {
    "金桥": "JQ",
    "银泰": "YT",
    "金银屯": "JYT",
    "金银潭": "JYT",
}

COUNTER_FILE = os.path.join(os.path.dirname(__file__), "..", "hlmc_counters.json")
HISTORY_FILE = os.path.join(os.path.dirname(__file__), "..", "hlmc_history.json")
_counter_lock = threading.Lock()


def _get_next_hlmc_order_no(shop_name: str) -> str:
    """
    生成并持久化欢乐牧场外部单号。
    格式：[缩写][YYMMDD][4位流水号]
    """
    prefix = "xx"
    for key, code in SHOP_ABBREVIATIONS.items():
        if key in shop_name:
            prefix = code
            break

    today_str = date.today().strftime("%y%m%d")

    with _counter_lock:
        current_data = {}
        if os.path.exists(COUNTER_FILE):
            try:
                with open(COUNTER_FILE, "r", encoding="utf-8") as f:
                    current_data = json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                current_data = {}

        if prefix not in current_data:
            current_data[prefix] = {"date": today_str, "count": 0}

        stored = current_data[prefix]

        if stored["date"] != today_str:
            stored["date"] = today_str
            stored["count"] = 0

        stored["count"] += 1
        count = stored["count"]

        try:
            with open(COUNTER_FILE, "w", encoding="utf-8") as f:
                json.dump(current_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Warning: Failed to update hlmc counter: {e}")

    return f"{prefix}{today_str}{count:04d}"


COUNTER_FILE = os.path.join(os.path.dirname(__file__), "..", "hlmc_counters.json")
HISTORY_FILE = os.path.join(os.path.dirname(__file__), "..", "hlmc_history.json")
_file_lock = threading.Lock()


def _safe_load_json(path: str) -> dict:
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            pass
    return {}


def _safe_save_json(path: str, data: dict):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except:
        pass


def parse_hlmc_excel(excel_path: str) -> Tuple[Dict[str, str], List[Dict[str, str]]]:
    """解析欢乐牧场 Excel 出库单"""
    wb = openpyxl.load_workbook(excel_path, data_only=True)
    ws = wb.active
    all_records: List[Dict[str, str]] = []

    today_str = date.today().strftime("%y%m%d")
    
    with _file_lock:
        counters = _safe_load_json(COUNTER_FILE)
        history = _safe_load_json(HISTORY_FILE)

    def ensure_counter(prefix):
        if prefix not in counters:
            counters[prefix] = {"date": today_str, "count": 0}
        stored = counters[prefix]
        if stored["date"] != today_str:
            stored["date"] = today_str
            stored["count"] = 0
        return stored

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
        if val == "冻结数量的总和": col_frozen = c
        elif val == "单位": col_unit = c
        elif val == "下单后结余": col_surplus = c
        elif val in ("SKU名称", "商品名称"): col_sku_name = c
        elif val == "外部商品编码": col_ext_code = c
        elif val == "商品编码" and not col_ext_code: col_ext_code = c
        elif val in ("库存单位", "单位"): col_sku_unit = c
        elif val == "规格": col_sku_spec = c

    if col_surplus is None:
        raise ValueError("欢乐牧场模板格式错误：找不到\"下单后结余\"列")

    shop_start = col_frozen if col_frozen else (col_unit if col_unit else 0)
    shop_cols: Dict[int, str] = {}
    for c in range(shop_start + 1, col_surplus):
        shop_name = str(header_row[c - 1].value or "").strip()
        if shop_name: shop_cols[c] = shop_name

    if not shop_cols:
        for c in range(1, col_surplus):
            v = header_row[c - 1].value
            if v and str(v).strip(): shop_cols[c] = str(v).strip()

    if not shop_cols:
        raise ValueError("欢乐牧场模板格式错误：找不到店铺列")

    def _match_store(shop_name: str) -> Dict[str, str]:
        for key, recv in HLMC_RECEIVERS.items():
            if key in shop_name: return recv
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
                except: qty_val = 0
                
                if qty_val > 0:
                    recv = _match_store(shop_name)
                    
                    prefix = "XX"
                    for key, code in SHOP_ABBREVIATIONS.items():
                        if key in shop_name: prefix = code; break
                    
                    stored_counter = ensure_counter(prefix)
                    
                    qty_int = int(qty_val)
                    sig = f"{shop_name}|{ext_code}|{qty_int}"
                    
                    order_no = None
                    if prefix in history:
                        if sig in history[prefix]:
                            order_no = history[prefix][sig]

                    if order_no is None:
                        stored_counter["count"] += 1
                        new_count = stored_counter["count"]
                        order_no = f"{prefix}{today_str}{new_count:04d}"
                        
                        if prefix not in history:
                            history[prefix] = {}
                        history[prefix][sig] = order_no

                    all_records.append({
                        "item_code": str(ext_code or "").strip(),
                        "item_name": str(sku_name or "").strip(),
                        "quantity": str(qty_int),
                        "unit": sku_unit,
                        "spec": sku_spec,
                        "category": "",
                        "remark": "",
                        "receiver_org": shop_name,
                        "receiver_name": recv.get("name", ""),
                        "receiver_phone": recv.get("phone", ""),
                        "receiver_address": recv.get("address", ""),
                        "order_no": order_no,
                        "supplier_org": "",
                        "order_date": "",
                    })
        r += 1

    with _file_lock:
        _safe_save_json(COUNTER_FILE, counters)
        _safe_save_json(HISTORY_FILE, history)

    info = {
        "order_no": next(iter([all_records[0]["order_no"]])) if all_records else "",
        "receiver_org": "",
        "supplier_org": "",
        "receiver_name": "",
        "receiver_phone": "",
        "receiver_address": "",
        "order_date": "",
    }
    return info, all_records
