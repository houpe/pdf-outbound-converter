import sys
from pathlib import Path

import pytest

backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from parsers.pdf_parser import parse_header, parse_items


class TestParseHeader:

    def test_parse_all_fields_present(self):
        text = (
            "单据编号：PS2512210002001\n"
            "收货机构：测试门店A\n"
            "供货机构：中央厨房\n"
            "收货人：张三\n"
            "收货电话：13800138000\n"
            "收货地址：北京市朝阳区测试路1号\n"
            "订单日期：2024-12-21\n"
        )
        result = parse_header(text)
        assert result["order_no"] == "PS2512210002001"
        assert result["receiver_org"] == "测试门店A"
        assert result["supplier_org"] == "中央厨房"
        assert result["receiver_name"] == "张三"
        assert result["receiver_phone"] == "13800138000"
        assert result["receiver_address"] == "北京市朝阳区测试路1号"
        assert result["order_date"] == "2024-12-21"

    def test_parse_order_no_with_suffix(self):
        text = "单据编号：PS2512210002001 已确认\n"
        result = parse_header(text)
        assert result["order_no"] == "PS2512210002001"

    def test_parse_order_date_with_suffix(self):
        text = "订单日期：2024-12-21 09:30\n"
        result = parse_header(text)
        assert result["order_date"] == "2024-12-21"

    def test_parse_missing_fields_returns_empty(self):
        text = "单据编号：PS2512210002001\n"
        result = parse_header(text)
        assert result["order_no"] == "PS2512210002001"
        assert result["receiver_org"] == ""
        assert result["receiver_name"] == ""

    def test_parse_empty_text(self):
        result = parse_header("")
        assert result["order_no"] == ""
        assert result["receiver_org"] == ""

    def test_parse_single_char_receiver_name_duplicated(self):
        text = "收货人：张\n"
        result = parse_header(text)
        assert result["receiver_name"] == "张张"

    def test_parse_two_char_receiver_name_unchanged(self):
        text = "收货人：张三\n"
        result = parse_header(text)
        assert result["receiver_name"] == "张三"


class TestParseItems:

    def test_parse_single_valid_item(self):
        tables = [
            [["序号", "分类", "商品编码", "商品名称", "规格", "单位", "数量", "备注"],
             ["1", "冻品", "CODE001", "牛肉片", "500g/包", "包", "10", ""]]
        ]
        result = parse_items(tables)
        assert len(result) == 1
        assert result[0]["item_code"] == "CODE001"
        assert result[0]["item_name"] == "牛肉片"
        assert result[0]["spec"] == "500g/包"
        assert result[0]["quantity"] == "10"

    def test_parse_multiple_items(self):
        tables = [
            [["序号", "分类", "商品编码", "商品名称", "规格", "单位", "数量", "备注"],
             ["1", "冻品", "CODE001", "牛肉片", "500g/包", "包", "10", ""],
             ["2", "冻品", "CODE002", "羊肉卷", "300g/包", "包", "5", ""]]
        ]
        result = parse_items(tables)
        assert len(result) == 2
        assert result[0]["item_code"] == "CODE001"
        assert result[1]["item_code"] == "CODE002"

    def test_parse_skips_non_numeric_rows(self):
        tables = [
            [["总计", "", "", "", "", "", "15", ""]]
        ]
        result = parse_items(tables)
        assert len(result) == 0

    def test_parse_skips_short_rows(self):
        tables = [[["1", "冻品"]]]
        result = parse_items(tables)
        assert len(result) == 0

    def test_parse_skips_empty_rows(self):
        tables = [[None, None]]
        result = parse_items(tables)
        assert len(result) == 0

    def test_parse_handles_newline_in_spec(self):
        tables = [
            [["序号", "分类", "商品编码", "商品名称", "规格", "单位", "数量", "备注"],
             ["1", "冻品", "CODE001", "牛肉片", "500g\n/包", "包", "10", ""]]
        ]
        result = parse_items(tables)
        assert result[0]["spec"] == "500g/包"

    def test_parse_requires_code_and_name(self):
        tables = [
            [["序号", "分类", "商品编码", "商品名称", "规格", "单位", "数量", "备注"],
             ["1", "冻品", "", "只有名称", "500g", "包", "10", ""],
             ["2", "冻品", "CODE002", "", "300g", "包", "5", ""]]
        ]
        result = parse_items(tables)
        assert len(result) == 0

    def test_parse_multiple_tables(self):
        tables = [
            [["序号", "分类", "商品编码", "商品名称", "规格", "单位", "数量", "备注"],
             ["1", "冻品", "CODE001", "牛肉片", "500g", "包", "10", ""]],
            [["序号", "分类", "商品编码", "商品名称", "规格", "单位", "数量", "备注"],
             ["1", "冻品", "CODE002", "羊肉卷", "300g", "包", "5", ""]]
        ]
        result = parse_items(tables)
        assert len(result) == 2

    def test_parse_skips_zero_quantity(self):
        tables = [
            [["序号", "分类", "商品编码", "商品名称", "规格", "单位", "数量", "备注"],
             ["1", "冻品", "CODE001", "牛肉片", "500g", "包", "0", ""],
             ["2", "冻品", "CODE002", "羊肉卷", "300g", "包", "5", ""]]
        ]
        result = parse_items(tables)
        assert len(result) == 1
        assert result[0]["item_code"] == "CODE002"

    def test_parse_skips_negative_quantity(self):
        tables = [
            [["序号", "分类", "商品编码", "商品名称", "规格", "单位", "数量", "备注"],
             ["1", "冻品", "CODE001", "牛肉片", "500g", "包", "-1", ""]]
        ]
        result = parse_items(tables)
        assert len(result) == 0
