import sys
from pathlib import Path

import pytest

backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from schemas import SplitCodeCreate, BatchItem


class TestSplitCodeCreate:

    def test_valid_yes(self):
        model = SplitCodeCreate(code="ABC123", split="是")
        assert model.code == "ABC123"
        assert model.split == "是"

    def test_valid_no(self):
        model = SplitCodeCreate(code="DEF456", split="否")
        assert model.split == "否"

    def test_missing_code(self):
        with pytest.raises(Exception):
            SplitCodeCreate(split="是")

    def test_missing_split(self):
        with pytest.raises(Exception):
            SplitCodeCreate(code="ABC")

    def test_empty_values(self):
        model = SplitCodeCreate(code="", split="")
        assert model.code == ""
        assert model.split == ""

    def test_model_dump(self):
        model = SplitCodeCreate(code="X", split="是")
        d = model.model_dump()
        assert d == {"code": "X", "split": "是"}

    def test_model_validate_from_dict(self):
        model = SplitCodeCreate.model_validate({"code": "Y", "split": "否"})
        assert model.code == "Y"
        assert model.split == "否"


class TestBatchItem:

    def test_valid_empty_id(self):
        model = BatchItem(id="", code="ABC", split="是")
        assert model.id == ""
        assert model.code == "ABC"

    def test_valid_with_id(self):
        model = BatchItem(id="123", code="DEF", split="否")
        assert model.id == "123"

    def test_missing_code(self):
        with pytest.raises(Exception):
            BatchItem(id="", split="是")

    def test_missing_split(self):
        with pytest.raises(Exception):
            BatchItem(id="", code="ABC")

    def test_id_required(self):
        with pytest.raises(Exception):
            BatchItem(code="A", split="是")

    def test_id_default_empty_via_model_construct(self):
        model = BatchItem.model_construct(id="", code="A", split="是")
        assert model.id == ""

    def test_model_dump(self):
        model = BatchItem(id="X", code="Y", split="是")
        d = model.model_dump()
        assert d["id"] == "X"
        assert d["code"] == "Y"
        assert d["split"] == "是"

    def test_model_validate_from_dict(self):
        model = BatchItem.model_validate({"id": "old_id", "code": "new_code", "split": "否"})
        assert model.id == "old_id"
        assert model.code == "new_code"
        assert model.split == "否"
