import sys
from pathlib import Path

import pytest

backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from strategies import get_strategy, STRATEGY_REGISTRY
from strategies.qzz import QzzStrategy
from strategies.lmt import LmtStrategy
from strategies.hlmc import HlmcStrategy
from strategies.yss import YssStrategy


class TestRegistry:
    def test_all_strategies_registered(self):
        assert set(STRATEGY_REGISTRY.keys()) == {"qzz", "lmt", "hlmc", "yss"}

    def test_get_strategy_valid(self):
        assert isinstance(get_strategy("qzz"), QzzStrategy)
        assert isinstance(get_strategy("lmt"), LmtStrategy)
        assert isinstance(get_strategy("hlmc"), HlmcStrategy)
        assert isinstance(get_strategy("yss"), YssStrategy)

    def test_get_strategy_invalid(self):
        with pytest.raises(ValueError, match="Unknown template"):
            get_strategy("nonexistent")


class TestWarehouseMapping:
    def test_qzz_warehouse(self):
        assert get_strategy("qzz").warehouse_code == "ZTOWHHY001"

    def test_lmt_warehouse(self):
        assert get_strategy("lmt").warehouse_code == "ZTOWHHY001"

    def test_hlmc_warehouse(self):
        assert get_strategy("hlmc").warehouse_code == "ZTOWHHY001"

    def test_yss_warehouse(self):
        assert get_strategy("yss").warehouse_code == "ZTOCSYH002"


class TestValidateSplitCodes:
    def test_lmt_validates(self):
        assert get_strategy("lmt").validate_split_codes is True

    def test_qzz_no_validate(self):
        assert get_strategy("qzz").validate_split_codes is False

    def test_hlmc_no_validate(self):
        assert get_strategy("hlmc").validate_split_codes is False

    def test_yss_no_validate(self):
        assert get_strategy("yss").validate_split_codes is False


class TestRouteQuantity:
    def test_qzz_default_no_split(self):
        s = get_strategy("qzz")
        col9, col10 = s.route_quantity(10, "ANYCODE", {})
        assert col9 == ""
        assert col10 == 10

    def test_qzz_ignores_split_map(self):
        s = get_strategy("qzz")
        col9, col10 = s.route_quantity(10, "C1", {"c1": "是"})
        assert col9 == ""
        assert col10 == 10

    def test_lmt_split_yes_goes_col9(self):
        s = get_strategy("lmt")
        col9, col10 = s.route_quantity(7, "C1", {"c1": "是"})
        assert col9 == 7
        assert col10 == ""

    def test_lmt_split_no_goes_col10(self):
        s = get_strategy("lmt")
        col9, col10 = s.route_quantity(7, "C1", {"c1": "否"})
        assert col9 == ""
        assert col10 == 7

    def test_lmt_missing_defaults_col9(self):
        s = get_strategy("lmt")
        col9, col10 = s.route_quantity(5, "MISSING", {})
        assert col9 == 5
        assert col10 == ""

    def test_hlmc_split_yes_goes_col9(self):
        s = get_strategy("hlmc")
        col9, col10 = s.route_quantity(8, "S1", {"s1": "是"})
        assert col9 == 8
        assert col10 == ""

    def test_hlmc_split_no_goes_col10(self):
        s = get_strategy("hlmc")
        col9, col10 = s.route_quantity(8, "S1", {"s1": "否"})
        assert col9 == ""
        assert col10 == 8

    def test_hlmc_missing_defaults_col9(self):
        s = get_strategy("hlmc")
        col9, col10 = s.route_quantity(5, "MISSING", {})
        assert col9 == 5
        assert col10 == ""

    def test_yss_split_yes_goes_col9(self):
        s = get_strategy("yss")
        col9, col10 = s.route_quantity(10, "ZBWP2139", {"zbwp2139": "是"})
        assert col9 == 10
        assert col10 == ""

    def test_yss_split_no_goes_col10(self):
        s = get_strategy("yss")
        col9, col10 = s.route_quantity(10, "ZBWP2139", {"zbwp2139": "否"})
        assert col9 == ""
        assert col10 == 10

    def test_yss_missing_defaults_col10(self):
        s = get_strategy("yss")
        col9, col10 = s.route_quantity(10, "MISSING", {})
        assert col9 == ""
        assert col10 == 10


class TestLmtValidation:
    def test_validate_raises_on_missing(self):
        from fastapi import HTTPException
        s = get_strategy("lmt")
        items = [
            {"item_code": "C1", "item_name": "A", "source_file": "f.xlsx"},
            {"item_code": "MISSING", "item_name": "B", "source_file": "f.xlsx"},
        ]
        with pytest.raises(HTTPException) as exc:
            s.validate_items(items, {"c1": "是"})
        assert exc.value.status_code == 400
        assert "商品编码缺失" in exc.value.detail["error"]
        assert len(exc.value.detail["codes"]) == 1
        assert exc.value.detail["codes"][0]["code"] == "MISSING"

    def test_validate_passes_when_all_present(self):
        s = get_strategy("lmt")
        items = [
            {"item_code": "C1", "item_name": "A", "source_file": "f.xlsx"},
            {"item_code": "C2", "item_name": "B", "source_file": "f.xlsx"},
        ]
        s.validate_items(items, {"c1": "是", "c2": "否"})

    def test_validate_deduplicates_missing(self):
        from fastapi import HTTPException
        s = get_strategy("lmt")
        items = [
            {"item_code": "MISSING", "item_name": "A", "source_file": "f1.xlsx"},
            {"item_code": "MISSING", "item_name": "A", "source_file": "f2.xlsx"},
        ]
        with pytest.raises(HTTPException) as exc:
            s.validate_items(items, {})
        assert len(exc.value.detail["codes"]) == 1

    def test_non_lmt_validate_is_noop(self):
        s = get_strategy("qzz")
        items = [{"item_code": "MISSING", "item_name": "A", "source_file": "f.xlsx"}]
        s.validate_items(items, {})
