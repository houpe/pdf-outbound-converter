from dataclasses import dataclass, field
from typing import Optional, Literal

STANDARD_FIELDS = [
    "order_no", "receiver_org", "receiver_name", "receiver_phone",
    "receiver_address", "item_code", "item_name", "quantity",
]

ParseMode = Literal["table", "matrix_transpose", "card_split", "text_parse", "multi_sheet"]
FieldSource = Literal["header_column", "cell_position", "regex", "static", "transpose", "col_index"]
PositionMode = Literal["absolute", "relative_to_data_start", "relative_to_data_end"]
FileType = Literal["excel", "word", "pdf", "any"]


@dataclass
class FieldMapping:
    source: FieldSource = "header_column"
    description: str = ""
    header_name: str = ""
    row: Optional[int] = None
    col: Optional[int] = None
    position_mode: Optional[PositionMode] = None
    regex: Optional[str] = None
    static_value: Optional[str] = None
    value: Optional[str] = None
    group_index: Optional[int] = None


@dataclass
class SplitRouting:
    """拆零路由配置：决定商品数量填入 I列(二级单位) 还是 J列(最小单位)"""
    warehouse_code: str = ""              # 查哪个仓库的拆零表
    split_yes: str = "to_secondary"       # 拆零表=是 → to_secondary(I) / to_min_unit(J)
    split_no: str = "to_min_unit"         # 拆零表=否 → to_secondary(I) / to_min_unit(J)
    default_action: str = "to_min_unit"   # 拆零表未配置 → to_secondary(I) / to_min_unit(J)
    validate_missing: bool = False        # 缺失编码是否阻断转换


@dataclass
class TailRegion:
    offset_from_data_end: int = 0
    row_count: int = 5
    position_mode: str = "after_data"


@dataclass
class MatrixColumns:
    header_row_index: Optional[int] = None
    start_col_index: Optional[int] = None
    end_col_index: Optional[int] = None
    data_start_row_index: Optional[int] = None


@dataclass
class ParseRule:
    id: str = ""
    name: str = ""
    description: str = ""
    version: int = 1
    file_type: FileType = "any"
    mode: ParseMode = "table"
    header_row: Optional[int] = None
    skip_rows: Optional[int] = None
    data_start_row: Optional[int] = None
    data_end_pattern: Optional[str] = None
    tail_region: Optional[TailRegion] = None
    field_mappings: dict = field(default_factory=dict)
    group_by_column: Optional[str] = None
    matrix_columns: Optional[MatrixColumns] = None
    card_boundary_pattern: Optional[str] = None
    card_header_pattern: Optional[str] = None
    record_separator_pattern: Optional[str] = None
    item_extract_pattern: Optional[str] = None
    skip_patterns: list = field(default_factory=list)
    static_values: dict = field(default_factory=dict)
    multi_sheet: bool = False
    default_values: dict = field(default_factory=dict)
    split_routing: Optional[SplitRouting] = None
    created_at: str = ""
    updated_at: str = ""


@dataclass
class StandardOrder:
    order_no: str = ""
    receiver_org: str = ""
    receiver_name: str = ""
    receiver_phone: str = ""
    receiver_address: str = ""
    item_code: str = ""
    item_name: str = ""
    quantity: float = 0


@dataclass
class MergeCell:
    row: int = 0
    col: int = 0
    rowspan: int = 1
    colspan: int = 1


@dataclass
class RawSheet:
    name: str = ""
    rows: list = field(default_factory=list)
    raw_text: str = ""
    merge_info: list = field(default_factory=list)


@dataclass
class FileContent:
    file_name: str = ""
    file_type: FileType = "excel"
    sheets: list = field(default_factory=list)
    full_text: str = ""
    total_rows: int = 0


@dataclass
class ParseResult:
    success: bool = True
    data: list = field(default_factory=list)
    errors: list = field(default_factory=list)
    warnings: list = field(default_factory=list)
    rule_used: Optional[ParseRule] = None
    stats: dict = field(default_factory=dict)


@dataclass
class AIRuleGenerationResult:
    rule: ParseRule = field(default_factory=ParseRule)
    confidence: float = 0.0
    reasoning: str = ""
    uncertain_mappings: list = field(default_factory=list)
    file_analysis: str = ""


def parse_rule_from_dict(d: dict) -> ParseRule:
    tr = None
    if d.get("tailRegion"):
        t = d["tailRegion"]
        tr = TailRegion(
            offset_from_data_end=t.get("offsetFromDataEnd", 0),
            row_count=t.get("rowCount", 5),
            position_mode=t.get("positionMode", "after_data"),
        )
    sr = None
    if d.get("splitRouting"):
        s = d["splitRouting"]
        sr = SplitRouting(
            warehouse_code=s.get("warehouseCode", "") or s.get("warehouse_code", ""),
            split_yes=s.get("splitYes", "to_secondary") or s.get("split_yes", "to_secondary"),
            split_no=s.get("splitNo", "to_min_unit") or s.get("split_no", "to_min_unit"),
            default_action=s.get("defaultAction", "to_min_unit") or s.get("default_action", "to_min_unit"),
            validate_missing=bool(s.get("validateMissing", s.get("validate_missing", False))),
        )
    mc = None
    if d.get("matrixColumns"):
        m = d["matrixColumns"]
        mc = MatrixColumns(
            header_row_index=m.get("headerRowIndex"),
            start_col_index=m.get("startColIndex"),
            end_col_index=m.get("endColIndex"),
            data_start_row_index=m.get("dataStartRowIndex"),
        )
    fm = {}
    for k, v in d.get("fieldMappings", {}).items():
        if isinstance(v, dict):
            fm[k] = FieldMapping(
                source=v.get("source", "header_column"),
                description=v.get("description", ""),
                header_name=v.get("headerName", ""),
                row=v.get("row"),
                col=v.get("col"),
                position_mode=v.get("positionMode"),
                regex=v.get("regex"),
                static_value=v.get("staticValue") or v.get("value"),
                value=v.get("value"),
                group_index=v.get("groupIndex"),
            )
    return ParseRule(
        id=d.get("id", ""),
        name=d.get("name", ""),
        description=d.get("description", ""),
        version=d.get("version", 1),
        file_type=d.get("fileType", "any"),
        mode=d.get("mode", "table"),
        header_row=d.get("headerRow"),
        skip_rows=d.get("skipRows"),
        data_start_row=d.get("dataStartRow"),
        data_end_pattern=d.get("dataEndPattern"),
        tail_region=tr,
        field_mappings=fm,
        group_by_column=d.get("groupByColumn"),
        matrix_columns=mc,
        card_boundary_pattern=d.get("cardBoundaryPattern"),
        card_header_pattern=d.get("cardHeaderPattern"),
        record_separator_pattern=d.get("recordSeparatorPattern"),
        item_extract_pattern=d.get("itemExtractPattern"),
        skip_patterns=d.get("skipPatterns", []),
        static_values=d.get("staticValues", {}),
        multi_sheet=d.get("multiSheet", False),
        default_values=d.get("defaultValues", {}),
        split_routing=sr,
    )


def parse_rule_to_dict(rule: ParseRule) -> dict:
    d = {
        "id": rule.id, "name": rule.name, "description": rule.description,
        "version": rule.version, "fileType": rule.file_type, "mode": rule.mode,
    }
    if rule.header_row is not None: d["headerRow"] = rule.header_row
    if rule.skip_rows is not None: d["skipRows"] = rule.skip_rows
    if rule.data_start_row is not None: d["dataStartRow"] = rule.data_start_row
    if rule.data_end_pattern: d["dataEndPattern"] = rule.data_end_pattern
    if rule.tail_region:
        d["tailRegion"] = {
            "offsetFromDataEnd": rule.tail_region.offset_from_data_end,
            "rowCount": rule.tail_region.row_count,
            "positionMode": rule.tail_region.position_mode,
        }
    if rule.group_by_column: d["groupByColumn"] = rule.group_by_column
    if rule.matrix_columns:
        mc = {}
        if rule.matrix_columns.header_row_index is not None: mc["headerRowIndex"] = rule.matrix_columns.header_row_index
        if rule.matrix_columns.start_col_index is not None: mc["startColIndex"] = rule.matrix_columns.start_col_index
        if rule.matrix_columns.end_col_index is not None: mc["endColIndex"] = rule.matrix_columns.end_col_index
        if rule.matrix_columns.data_start_row_index is not None: mc["dataStartRowIndex"] = rule.matrix_columns.data_start_row_index
        if mc: d["matrixColumns"] = mc
    if rule.card_boundary_pattern: d["cardBoundaryPattern"] = rule.card_boundary_pattern
    if rule.card_header_pattern: d["cardHeaderPattern"] = rule.card_header_pattern
    if rule.record_separator_pattern: d["recordSeparatorPattern"] = rule.record_separator_pattern
    if rule.item_extract_pattern: d["itemExtractPattern"] = rule.item_extract_pattern
    if rule.skip_patterns: d["skipPatterns"] = rule.skip_patterns
    if rule.static_values: d["staticValues"] = rule.static_values
    if rule.multi_sheet: d["multiSheet"] = rule.multi_sheet
    if rule.default_values: d["defaultValues"] = rule.default_values
    if rule.split_routing:
        sr = rule.split_routing
        d["splitRouting"] = {
            "warehouseCode": sr.warehouse_code,
            "splitYes": sr.split_yes,
            "splitNo": sr.split_no,
            "defaultAction": sr.default_action,
            "validateMissing": sr.validate_missing,
        }
    fm = {}
    for k, m in rule.field_mappings.items():
        obj = {"source": m.source}
        if m.description: obj["description"] = m.description
        if m.header_name: obj["headerName"] = m.header_name
        if m.row is not None: obj["row"] = m.row
        if m.col is not None: obj["col"] = m.col
        if m.position_mode: obj["positionMode"] = m.position_mode
        if m.regex: obj["regex"] = m.regex
        if m.static_value: obj["staticValue"] = m.static_value
        if m.group_index is not None: obj["groupIndex"] = m.group_index
        fm[k] = obj
    d["fieldMappings"] = fm
    return d
