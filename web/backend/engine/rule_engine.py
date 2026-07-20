import re
from typing import Optional
from engine.types import (
    FileContent, ParseRule, StandardOrder, ParseResult, RawSheet, FieldMapping,
)


class RuleEngine:
    def parse(self, file_content: FileContent, rule: ParseRule) -> ParseResult:
        import time
        start = time.time()
        try:
            if rule.mode == "table":
                result = self._parse_table(file_content, rule)
            elif rule.mode == "matrix_transpose":
                result = self._parse_matrix_transpose(file_content, rule)
            elif rule.mode == "card_split":
                result = self._parse_card_split(file_content, rule)
            elif rule.mode == "text_parse":
                result = self._parse_text(file_content, rule)
            elif rule.mode == "multi_sheet":
                result = self._parse_multi_sheet(file_content, rule)
            else:
                result = self._fail(rule, f"不支持的解析模式: {rule.mode}")
            result.stats = {
                "total_rows": file_content.total_rows or sum(len(s.rows) for s in file_content.sheets),
                "parsed_rows": len(result.data),
                "skipped_rows": 0,
                "duration_ms": int((time.time() - start) * 1000),
            }
            return result
        except Exception as e:
            return ParseResult(
                success=False, errors=[f"解析异常: {e}"], rule_used=rule,
                stats={"total_rows": 0, "parsed_rows": 0, "skipped_rows": 0, "duration_ms": int((time.time() - start) * 1000)},
            )

    def _parse_table(self, fc: FileContent, rule: ParseRule) -> ParseResult:
        sheet = fc.sheets[0] if fc.sheets else None
        if not sheet:
            return self._fail(rule, "文件无数据")
        header_row_idx = rule.header_row if rule.header_row is not None else 0
        data_start = rule.data_start_row if rule.data_start_row is not None else header_row_idx + 1
        data_start = max(data_start, header_row_idx + 1)
        header_row = sheet.rows[header_row_idx] if header_row_idx < len(sheet.rows) else []
        col_idx_map = self._build_col_index_map(header_row, rule)
        data_end = len(sheet.rows)
        if rule.data_end_pattern:
            end_re = re.compile(rule.data_end_pattern)
            for i in range(data_start, len(sheet.rows)):
                if end_re.search(self._row_to_text(sheet.rows[i])):
                    data_end = i
                    break
        raw_rows = []
        for i in range(data_start, data_end):
            row = sheet.rows[i]
            if not row:
                continue
            if self._should_skip(row, rule.skip_patterns):
                continue
            if self._is_empty(row):
                continue
            if self._is_header_row(row, header_row):
                continue
            if self._is_summary_row(row):
                continue
            if self._is_title_row(row, header_row):
                continue
            raw_rows.append(self._map_row(row, col_idx_map, rule, i))
        header_fields = self._extract_header_fields(sheet, rule, data_start)
        orders = self._group_and_convert(raw_rows, rule, sheet, data_end, header_fields)
        orders = [o for o in orders if not self._is_invalid_order(o)]
        return ParseResult(success=True, data=orders, rule_used=rule)

    def _parse_matrix_transpose(self, fc: FileContent, rule: ParseRule) -> ParseResult:
        sheet = fc.sheets[0] if fc.sheets else None
        if not sheet:
            return self._fail(rule, "文件无数据")
        mc = rule.matrix_columns
        if not mc:
            return self._fail(rule, "矩阵转置模式需配置 matrixColumns")
        header_row_idx = mc.header_row_index if mc.header_row_index is not None else (rule.header_row or 0)
        header_row = sheet.rows[header_row_idx] if header_row_idx < len(sheet.rows) else []
        data_start = mc.data_start_row_index if mc.data_start_row_index is not None else (rule.data_start_row or header_row_idx + 1)
        data_end = len(sheet.rows)
        if rule.data_end_pattern:
            end_re = re.compile(rule.data_end_pattern)
            for i in range(data_start, len(sheet.rows)):
                if end_re.search(self._row_to_text(sheet.rows[i])):
                    data_end = i
                    break
        start_col = mc.start_col_index
        end_col = mc.end_col_index
        if start_col is None or end_col is None:
            sku_cols = []
            for mapping in rule.field_mappings.values():
                if mapping.source == "col_index" and mapping.col is not None:
                    sku_cols.append(mapping.col)
                elif mapping.source == "header_column" and mapping.header_name:
                    for i, c in enumerate(header_row):
                        if mapping.header_name in str(c or ""):
                            sku_cols.append(i)
                            break
            max_sku = max(sku_cols) if sku_cols else 7
            summary_kw = ["合计", "总计", "小计", "汇总", "结余", "sum", "total"]
            store_cols = []
            for c in range(max_sku + 1, len(header_row)):
                h = str(header_row[c] or "").strip()
                if h and not any(k in h.lower() for k in summary_kw):
                    store_cols.append(c)
            start_col = store_cols[0] if store_cols else max_sku + 1
            end_col = store_cols[-1] if store_cols else start_col
        orders = []
        summary_kw2 = ["合计", "总计", "小计", "汇总", "结余"]
        for col_idx in range(start_col, end_col + 1):
            store_name = str(header_row[col_idx] or "").strip() if col_idx < len(header_row) else ""
            if not store_name or any(k in store_name for k in summary_kw2):
                continue
            for row_idx in range(data_start, data_end):
                row = sheet.rows[row_idx] if row_idx < len(sheet.rows) else None
                if not row or self._is_empty(row) or self._is_summary_row(row):
                    continue
                cell_val = str(row[col_idx] or "").strip() if col_idx < len(row) else ""
                if not cell_val or cell_val == "0":
                    continue
                try:
                    qty = float(cell_val)
                except (ValueError, TypeError):
                    continue
                if qty <= 0:
                    continue
                order = StandardOrder(receiver_org=store_name, quantity=qty)
                for fld, mapping in rule.field_mappings.items():
                    if mapping.source == "transpose":
                        continue
                    if mapping.source == "col_index" and mapping.col is not None:
                        val = row[mapping.col] if mapping.col < len(row) else None
                        if val is not None:
                            self._set_field(order, fld, str(val))
                    elif mapping.source == "header_column" and mapping.header_name:
                        ci = None
                        for i, c in enumerate(header_row):
                            if mapping.header_name in str(c or ""):
                                ci = i
                                break
                        if ci is not None and ci < len(row) and row[ci] is not None:
                            self._set_field(order, fld, str(row[ci]))
                    elif mapping.source == "static":
                        sv = mapping.static_value or mapping.value or ""
                        if sv:
                            self._set_field(order, fld, sv)
                self._apply_defaults(order, rule)
                if not self._is_invalid_order(order):
                    orders.append(order)
        return ParseResult(success=True, data=orders, rule_used=rule)

    def _parse_card_split(self, fc: FileContent, rule: ParseRule) -> ParseResult:
        sheet = fc.sheets[0] if fc.sheets else None
        if not sheet:
            return self._fail(rule, "文件无数据")
        boundary_pat = rule.card_boundary_pattern or r"^▶"
        boundary_re = re.compile(boundary_pat)
        cards = []
        cur_start = -1
        for i in range(len(sheet.rows)):
            if boundary_re.search(self._row_to_text(sheet.rows[i])):
                if cur_start >= 0:
                    cards.append((cur_start, i - 1))
                cur_start = i
        if cur_start >= 0:
            cards.append((cur_start, len(sheet.rows) - 1))
        orders = []
        for start, end in cards:
            card_rows = sheet.rows[start:end + 1]
            orders.extend(self._parse_single_card(card_rows, rule))
        orders = [o for o in orders if not self._is_invalid_order(o)]
        return ParseResult(success=True, data=orders, rule_used=rule)

    def _parse_single_card(self, card_rows: list, rule: ParseRule) -> list:
        header_pat = rule.card_header_pattern or "编码|物品|SKU"
        header_idx = -1
        for i, row in enumerate(card_rows):
            if re.search(header_pat, self._row_to_text(row)):
                header_idx = i
                break
        base = StandardOrder()
        for i, row in enumerate(card_rows):
            if i == header_idx:
                continue
            self._extract_regex_fields(self._row_to_text(row), rule.field_mappings, base)
        for fld, mapping in rule.field_mappings.items():
            if mapping.source == "cell_position" and mapping.row is not None and mapping.col is not None:
                if 0 <= mapping.row < len(card_rows):
                    r = card_rows[mapping.row]
                    if r and mapping.col < len(r) and r[mapping.col] is not None:
                        val = str(r[mapping.col]).strip()
                        if val:
                            cur = self._get_field(base, fld)
                            if not cur or not cur.strip():
                                self._set_field(base, fld, val)
        if header_idx < 0:
            self._apply_defaults(base, rule)
            return [base]
        header_row = card_rows[header_idx]
        col_map = self._build_col_index_map(header_row, rule)
        orders = []
        for i in range(header_idx + 1, len(card_rows)):
            row = card_rows[i]
            if not row or self._is_empty(row):
                continue
            if self._should_skip(row, rule.skip_patterns) or self._is_summary_row(row):
                continue
            record = self._map_row(row, col_map, rule, i)
            order = StandardOrder(
                order_no=base.order_no, receiver_org=base.receiver_org,
                receiver_name=base.receiver_name, receiver_phone=base.receiver_phone,
                receiver_address=base.receiver_address,
            )
            for f, v in record.items():
                if v:
                    self._set_field(order, f, v)
            self._apply_defaults(order, rule)
            if not self._is_invalid_order(order):
                orders.append(order)
        return orders if orders else [base]

    def _parse_text(self, fc: FileContent, rule: ParseRule) -> ParseResult:
        text = fc.full_text or ""
        if not text:
            return self._fail(rule, "文件无文本内容")
        sep = (rule.record_separator_pattern or "").strip()
        blocks = [b for b in (re.split(sep, text) if sep else [text]) if b.strip()] if sep else [text]
        orders = []
        for block in blocks:
            base = StandardOrder()
            for line in block.split("\n"):
                if line.strip():
                    self._extract_regex_fields(line, rule.field_mappings, base)
            if rule.item_extract_pattern:
                items = re.findall(rule.item_extract_pattern, block)
                if items:
                    for groups in items:
                        item_order = StandardOrder(
                            order_no=base.order_no, receiver_org=base.receiver_org,
                            receiver_name=base.receiver_name, receiver_phone=base.receiver_phone,
                            receiver_address=base.receiver_address,
                        )
                        for fld, mapping in rule.field_mappings.items():
                            if mapping.source == "regex" and mapping.group_index is not None:
                                if mapping.group_index < len(groups):
                                    val = groups[mapping.group_index].strip()
                                    if val:
                                        self._set_field(item_order, fld, val)
                        self._apply_defaults(item_order, rule)
                        orders.append(item_order)
                    continue
            self._apply_defaults(base, rule)
            orders.append(base)
        return ParseResult(success=True, data=orders, rule_used=rule)

    def _parse_multi_sheet(self, fc: FileContent, rule: ParseRule) -> ParseResult:
        all_orders, all_errors, all_warnings = [], [], []
        for sheet in fc.sheets:
            single_fc = FileContent(
                file_name=fc.file_name, file_type=fc.file_type,
                sheets=[sheet], full_text=sheet.raw_text,
            )
            inner_rule = ParseRule(
                **{k: v for k, v in rule.__dict__.items() if k != "mode" and k != "multi_sheet"},
                mode="table", multi_sheet=False,
            )
            r = self._parse_table(single_fc, inner_rule)
            all_orders.extend(r.data)
            all_errors.extend(r.errors)
            all_warnings.extend(r.warnings)
        return ParseResult(success=not all_errors, data=all_orders, errors=all_errors, warnings=all_warnings, rule_used=rule)

    def _build_col_index_map(self, header_row: list, rule: ParseRule) -> dict:
        col_map = {}
        for fld, mapping in rule.field_mappings.items():
            if mapping.source == "header_column" and mapping.header_name:
                names = [n.strip() for n in mapping.header_name.split("|")]
                for i, cell in enumerate(header_row):
                    cv = str(cell or "").strip()
                    if any(n in cv for n in names):
                        col_map[fld] = i
                        break
        return col_map

    def _map_row(self, row: list, col_map: dict, rule: ParseRule, abs_row: int) -> dict:
        record = {}
        for fld, mapping in rule.field_mappings.items():
            if mapping.source == "header_column":
                col = col_map.get(fld)
                if col is not None and col < len(row) and row[col] is not None:
                    record[fld] = str(row[col])
            elif mapping.source == "cell_position":
                target = self._resolve_pos(mapping, rule, abs_row)
                if target == abs_row and mapping.col is not None and mapping.col < len(row) and row[mapping.col] is not None:
                    record[fld] = str(row[mapping.col])
            elif mapping.source == "static":
                record[fld] = mapping.static_value or mapping.value or ""
            elif mapping.source == "regex":
                text = self._row_to_text(row)
                if mapping.regex:
                    m = re.search(mapping.regex, text)
                    if m and len(m.groups()) >= 1:
                        record[fld] = m.group(1).strip()
            elif mapping.source == "col_index":
                if mapping.col is not None and mapping.col < len(row) and row[mapping.col] is not None:
                    record[fld] = str(row[mapping.col])
        return record

    def _resolve_pos(self, mapping: FieldMapping, rule: ParseRule, fallback: int) -> int:
        if mapping.row is None:
            return fallback
        mode = mapping.position_mode or "absolute"
        if mode == "absolute":
            return mapping.row
        elif mode == "relative_to_data_start":
            return (rule.data_start_row or 0) + mapping.row
        elif mode == "relative_to_data_end":
            return fallback + mapping.row
        return mapping.row

    def _extract_header_fields(self, sheet: RawSheet, rule: ParseRule, data_start: int) -> dict:
        result = {}
        for fld, mapping in rule.field_mappings.items():
            if mapping.source == "cell_position" and mapping.row is not None:
                target = self._resolve_pos(mapping, rule, mapping.row)
                if 0 <= target < data_start and target < len(sheet.rows):
                    row = sheet.rows[target]
                    if row and mapping.col is not None and mapping.col < len(row) and row[mapping.col] is not None:
                        val = str(row[mapping.col]).strip()
                        if val:
                            result[fld] = val
            if mapping.source == "regex" and mapping.regex:
                for i in range(min(data_start, len(sheet.rows))):
                    row = sheet.rows[i]
                    if not row:
                        continue
                    text = self._row_to_text(row)
                    m = re.search(mapping.regex, text)
                    if m and len(m.groups()) >= 1:
                        val = m.group(1).strip()
                        if val and (fld not in result or not result[fld].strip()):
                            result[fld] = val
                            break
        return result

    def _extract_tail_fields(self, sheet: RawSheet, rule: ParseRule, data_end: int) -> dict:
        result = {}
        tr = rule.tail_region
        if not tr:
            if data_end < len(sheet.rows):
                self._scan_rows(sheet, rule, data_end, len(sheet.rows), result)
            return result
        start = tr.offset_from_data_end if tr.position_mode == "absolute_start" else data_end + tr.offset_from_data_end
        if start >= len(sheet.rows):
            self._scan_rows(sheet, rule, 0, len(sheet.rows), result)
            return result
        self._scan_rows(sheet, rule, start, len(sheet.rows), result)
        return result

    def _scan_rows(self, sheet: RawSheet, rule: ParseRule, from_row: int, to_row: int, result: dict):
        for i in range(from_row, min(to_row, len(sheet.rows))):
            row = sheet.rows[i]
            if not row:
                continue
            text = self._row_to_text(row)
            for fld, mapping in rule.field_mappings.items():
                if result.get(fld, "").strip():
                    continue
                if mapping.source == "regex" and mapping.regex:
                    m = re.search(mapping.regex, text)
                    if m and len(m.groups()) >= 1:
                        val = m.group(1).strip()
                        if val:
                            result[fld] = val
                if mapping.source == "cell_position":
                    target = self._resolve_pos(mapping, rule, i)
                    if target == i and mapping.col is not None and mapping.col < len(row) and row[mapping.col] is not None:
                        val = str(row[mapping.col]).strip()
                        if val:
                            result[fld] = val

    def _group_and_convert(self, raw_rows: list, rule: ParseRule, sheet: RawSheet, data_end: int, header_fields: dict = None) -> list:
        header_fields = header_fields or {}
        tail_fields = self._extract_tail_fields(sheet, rule, data_end)
        if rule.group_by_column:
            groups = {}
            for row in raw_rows:
                key = row.get(rule.group_by_column, f"__ungrouped_{len(groups)}")
                groups.setdefault(key, []).append(row)
            orders = []
            for key, rows in groups.items():
                for row in rows:
                    order = self._record_to_order(row)
                    if key and not key.startswith("__"):
                        order.order_no = order.order_no or key
                    self._merge(order, header_fields)
                    self._merge(order, tail_fields)
                    self._apply_defaults(order, rule)
                    orders.append(order)
            return orders
        orders = []
        for row in raw_rows:
            order = self._record_to_order(row)
            self._merge(order, header_fields)
            self._merge(order, tail_fields)
            self._apply_defaults(order, rule)
            orders.append(order)
        return orders

    def _extract_regex_fields(self, text: str, mappings: dict, order: StandardOrder):
        for fld, mapping in mappings.items():
            if mapping.source == "regex" and mapping.regex:
                m = re.search(mapping.regex, text)
                if m and len(m.groups()) >= 1:
                    self._set_field(order, fld, m.group(1).strip())

    def _record_to_order(self, record: dict) -> StandardOrder:
        order = StandardOrder()
        for fld, val in record.items():
            if val:
                self._set_field(order, fld, val)
        return order

    def _merge(self, order: StandardOrder, fields: dict):
        for fld, val in fields.items():
            cur = self._get_field(order, fld)
            if not cur or not cur.strip():
                self._set_field(order, fld, val)

    def _apply_defaults(self, order: StandardOrder, rule: ParseRule):
        if rule.default_values:
            for fld, val in rule.default_values.items():
                cur = self._get_field(order, fld)
                if fld == "quantity":
                    if order.quantity == 0 and val:
                        try:
                            order.quantity = float(val)
                        except (ValueError, TypeError):
                            pass
                elif not cur or not cur.strip():
                    self._set_field(order, fld, val)
        if rule.static_values:
            for fld, val in rule.static_values.items():
                self._set_field(order, fld, val)

    def _set_field(self, order: StandardOrder, field: str, value: str):
        if field == "order_no": order.order_no = value
        elif field == "receiver_org": order.receiver_org = value
        elif field == "receiver_name": order.receiver_name = value
        elif field == "receiver_phone": order.receiver_phone = value
        elif field == "receiver_address": order.receiver_address = value
        elif field == "item_code": order.item_code = value
        elif field == "item_name": order.item_name = value
        elif field == "quantity":
            try: order.quantity = float(value)
            except (ValueError, TypeError): pass

    def _get_field(self, order: StandardOrder, field: str) -> str:
        if field == "order_no": return order.order_no
        elif field == "receiver_org": return order.receiver_org
        elif field == "receiver_name": return order.receiver_name
        elif field == "receiver_phone": return order.receiver_phone
        elif field == "receiver_address": return order.receiver_address
        elif field == "item_code": return order.item_code
        elif field == "item_name": return order.item_name
        elif field == "quantity": return str(order.quantity)
        return ""

    def _row_to_text(self, row) -> str:
        if not row:
            return ""
        return " ".join(str(c or "") for c in row)

    def _is_empty(self, row) -> bool:
        return all(c is None or str(c).strip() == "" for c in row)

    def _is_header_row(self, row, header_row) -> bool:
        header_texts = [str(c or "").strip().lower() for c in header_row]
        match_count = 0
        checked = 0
        for i in range(min(len(row), len(header_row))):
            cv = str(row[i] or "").strip().lower()
            hv = header_texts[i]
            if not hv:
                continue
            checked += 1
            if cv == hv:
                match_count += 1
        if checked >= 3 and match_count >= 2:
            return True
        kw = ["序号", "编号", "编码", "名称", "品名", "物品", "商品", "规格", "型号",
               "数量", "单位", "单价", "金额", "合计", "备注", "类别", "sku", "门店"]
        non_empty = [c for c in row if str(c or "").strip()]
        if len(non_empty) >= 3:
            kw_match = sum(1 for c in non_empty if any(k in str(c).lower() for k in kw))
            if kw_match >= len(non_empty) * 0.6:
                return True
        return False

    def _is_summary_row(self, row) -> bool:
        patterns = [r"^合计$", r"^小计$", r"^汇总$", r"^总计$", r"^total$", r"^subtotal$", r"^sum$"]
        for c in row:
            v = str(c or "").strip()
            if v and any(re.search(p, v, re.IGNORECASE) for p in patterns):
                return True
        return False

    def _is_title_row(self, row, header_row) -> bool:
        non_empty = [c for c in row if str(c or "").strip()]
        if len(non_empty) != 1:
            return False
        val = str(non_empty[0]).strip()
        if re.match(r"^\d+(\.\d+)?$", val):
            return False
        indicators = [r"第\d+页", r"共\d+页", r"打印", r"制表", r"备注[：:]", r"收货人签字", r"审核"]
        return any(re.search(p, val) for p in indicators)

    def _is_invalid_order(self, order: StandardOrder) -> bool:
        no_code = not order.item_code or not order.item_code.strip()
        no_name = not order.item_name or not order.item_name.strip()
        return no_code and no_name

    def _should_skip(self, row, patterns: list) -> bool:
        if not patterns:
            return False
        text = self._row_to_text(row)
        return any(re.search(p, text) for p in patterns)

    def _fail(self, rule: ParseRule, *errors: str) -> ParseResult:
        return ParseResult(success=False, errors=list(errors), rule_used=rule)
