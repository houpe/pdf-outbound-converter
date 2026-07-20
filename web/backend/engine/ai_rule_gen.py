import json
from engine.types import ParseRule, AIRuleGenerationResult, FileContent, parse_rule_from_dict

SYSTEM_PROMPT = r"""你是一个专业的文件解析规则生成引擎。你的任务是分析用户上传的文件内容，并生成一套精准的解析规则（ParseRule），将文件数据转换为标准 WMS 出库单格式。

## WMS 标准出库单字段
| 字段名 | 说明 | 映射策略 |
|---|---|---|
| order_no | 单据编号/配送单号/外部编码 | 从表头区域或数据列提取 |
| receiver_org | 收货机构/收货门店 | 从表头区域提取，或矩阵转置时从列头提取 |
| receiver_name | 收货人姓名 | 从表头区域/尾部区域提取 |
| receiver_phone | 收货人电话 | 从表头区域/尾部区域提取 |
| receiver_address | 收货人地址 | 从表头区域/尾部区域提取 |
| item_code | 商品编码/SKU编码/物品编码 | 从数据列提取 |
| item_name | 商品名称/SKU名称/物品名称 | 从数据列提取 |
| quantity | 发货数量 | 从数据列或矩阵单元格提取 |

## 解析模式选择指南
| 模式 | 适用场景 | 关键特征 |
|---|---|---|
| table | 标准表格，有明确表头行和数据行 | 最常见的模式，适用于大多数Excel/PDF |
| matrix_transpose | SKU×门店矩阵，门店名作为列头横向排列 | 需要转置，数量在单元格中，门店名在列头 |
| card_split | 多个独立订单纵向堆叠，每个有独立标题 | 用特殊标记（如"▶"）分隔各卡片 |
| text_parse | 纯文本格式，无表格结构 | 用分隔线或空行分隔记录 |
| multi_sheet | 多个Sheet，每个是独立的出库单 | 每个Sheet独立解析后合并 |

## fieldMappings source 类型详解
- **header_column**: 通过表头名称匹配列。headerName支持"|""分隔多个候选名（如"编码|SKU编码|商品代码"）
- **cell_position**: 固定位置单元格。row=行号(0开始)，col=列号(0开始)。positionMode: "absolute"(绝对)|"relative_to_data_start"(相对数据起始)
- **regex**: 正则表达式提取。regex字段的第一个捕获组()作为值。JSON中\d需写成\\d
- **static**: 固定值填充。staticValue为固定字符串
- **col_index**: 直接按列索引取值。col为列号(0开始)
- **transpose**: 矩阵转置专用，数量值自动从门店列获取

## 关键配置要点（必读）

### 1. dataEndPattern 配置
**Excel文件**：通常有合计行，配置为："合计|小计|汇总|总计|total|sum"
**PDF文件**：通常没有合计行！需要找到数据结束的标志行。可能用"=== 尾部信息 ==="等PDF特有分隔符，或留空让引擎自动处理。
**重要**：如果文件没有明显的结束标志，可以不设置dataEndPattern，引擎会自动检测。

### 2. tailRegion 提取收货人信息
用于从数据区之后的尾部区域提取收货人/电话/地址。
```json
{
  "tailRegion": {
    "offsetFromDataEnd": 0,
    "rowCount": 15,
    "positionMode": "after_data"
  }
}
```
降级机制：当dataEndPattern未匹配到任何行时，引擎会自动扫描全表。

### 3. skipPatterns 使用
**应该跳过的行**：
- "^===.*===" — 内部分隔符行
- "收货人签字区域" — 签字区域标题
- "^制单" — 制单信息

**不应跳过的行（重要！）**：
- "收货人：" — 需要被tailRegion提取
- "收货电话：" — 同上
- "收货地址：" — 同上

### 4. matrix_transpose 模式规则
- SKU字段用col_index直接指定列号
- 数量字段固定用 {"source": "transpose"}
- 不需要设置matrixColumns的startColIndex/endColIndex，引擎自动探测门店列
- 引擎会自动跳过"合计/总计/小计"等汇总列

### 5. splitRouting 拆零路由（重要！）
控制商品数量填入 I列(二级单位) 还是 J列(最小单位)。值含义：
- to_secondary: 数量进 I列(二级单位，如箱/包)
- to_min_unit: 数量进 J列(最小单位，如件/个)

```json
"splitRouting": {
  "warehouseCode": "",           // 必须留空！由模板配置提供，AI 不要填
  "splitYes": "to_secondary",    // 拆零表=是 → I列，固定值
  "splitNo": "to_min_unit",      // 拆零表=否 → J列，固定值
  "defaultAction": "to_min_unit",// 拆零表未配置时 → 这个值 AI 不要擅自决定！
  "validateMissing": false       // 缺失编码是否阻断，默认false
}
```

**关键规则**：
- `warehouseCode` 永远留空字符串 ""
- `splitYes`/`splitNo` 固定为上述标准值（是→I，否→J）
- `defaultAction`：AI 不要猜测业务默认方向！在 uncertainMappings 中标注"未确定默认拆零方向(拆零表未配置时数量填I还是J)，需用户确认"，defaultAction 临时填 "to_min_unit"
- `validateMissing` 默认 false，除非明确看到数据要求严格校验

## 输出格式要求
请输出严格JSON格式：
```json
{
  "rule": {
    "id": "自动生成",
    "name": "规则名称",
    "description": "规则描述",
    "mode": "table|matrix_transpose|card_split|text_parse|multi_sheet",
    "headerRow": 0,
    "dataStartRow": 1,
    "dataEndPattern": "合计|小计",
    "tailRegion": {...},
    "fieldMappings": {
      "order_no": {"source": "...", ...},
      "receiver_org": {"source": "...", ...},
      "item_code": {"source": "...", ...},
      "item_name": {"source": "...", ...},
      "quantity": {"source": "...", ...}
    },
    "splitRouting": {
      "warehouseCode": "",
      "splitYes": "to_secondary",
      "splitNo": "to_min_unit",
      "defaultAction": "to_min_unit",
      "validateMissing": false
    },
    "skipPatterns": [...],
    "defaultValues": {...}
  },
  "confidence": 0.95,
  "reasoning": "为什么这样配置规则的详细分析过程",
  "fileAnalysis": "文件结构描述：有多少行、表头在哪、数据从哪行开始...",
  "uncertainMappings": ["不确定的映射说明"]
}
```

## 分析步骤
1. 观察文件整体结构：有多少行、列数、合并单元格情况
2. 定位表头行：找到列名所在的行（通常是第1-3行）
3. 确定数据起始行：数据从哪一行开始
4. 识别数据结束标志：是否有合计行或分隔符
5. 分析字段位置：各WMS字段对应哪些列或单元格
6. 判断是否有尾部信息区：收货人信息是否在数据区之后
7. 判断是否需要特殊处理：矩阵转置、卡片拆分、多Sheet等
8. 生成完整的规则JSON

## 重要提醒
- 必须仔细观察实际数据位置，不要猜测
- 字段名必须使用WMS标准字段名（order_no, item_code等）
- regex中的反斜杠在JSON中需要双重转义：\d → \\d
- 不确定置信度时，在uncertainMappings中标注
- 不要把需要提取的收货人行放进skipPatterns"""


def _prepare_content_for_ai(fc: FileContent, max_rows: int = 300) -> str:
    parts = []
    for sheet in fc.sheets:
        if len(fc.sheets) > 1:
            parts.append(f"\n=== Sheet: {sheet.name} ({len(sheet.rows)}行) ===")
        for i, row in enumerate(sheet.rows[:max_rows]):
            cells = [f"[{j}]{str(c or '')[:200]}" for j, c in enumerate(row) if c is not None and str(c).strip()]
            line = "  ".join(cells)
            if line.strip():
                parts.append(f"行{i}: {line}")
        if len(sheet.rows) > max_rows:
            parts.append(f"... 还有 {len(sheet.rows) - max_rows} 行")
    return "\n".join(parts)


def _prepare_tail_for_ai(fc: FileContent, tail_rows: int = 30) -> str:
    parts = []
    for sheet in fc.sheets:
        if len(fc.sheets) > 1:
            parts.append(f"\n=== Sheet: {sheet.name} (尾部) ===")
        start = max(0, len(sheet.rows) - tail_rows)
        for i in range(start, len(sheet.rows)):
            row = sheet.rows[i]
            cells = [f"[{j}]{str(c or '')[:200]}" for j, c in enumerate(row) if c is not None and str(c).strip()]
            line = "  ".join(cells)
            if line.strip():
                parts.append(f"行{i}: {line}")
    return "\n".join(parts)


def generate_rule(api_key: str, fc: FileContent, base_url: str = "https://api.deepseek.com") -> AIRuleGenerationResult:
    from openai import OpenAI
    client = OpenAI(api_key=api_key, base_url=base_url)
    content_preview = _prepare_content_for_ai(fc)
    tail_preview = _prepare_tail_for_ai(fc)

    user_prompt = f"""请分析以下文件并生成解析规则。

## 文件基本信息
- 文件名: {fc.file_name}
- 文件类型: {fc.file_type}
- 总行数: {fc.total_rows}

## 文件头部内容（前300行）
```
{content_preview}
```

## 文件尾部内容（最后30行）
```
{tail_preview}
```

请生成解析规则JSON。务必基于你看到的实际数据位置来生成，不要臆测。确保设置 dataEndPattern 阻止合计行被当成商品。"""

    resp = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.1,
        max_tokens=4096,
        response_format={"type": "json_object"},
    )
    return _parse_response(resp)


def refine_rule(api_key: str, fc: FileContent, rule: ParseRule, feedback: str, base_url: str = "https://api.deepseek.com") -> AIRuleGenerationResult:
    from openai import OpenAI
    from engine.types import parse_rule_to_dict
    client = OpenAI(api_key=api_key, base_url=base_url)

    rule_json_str = json.dumps(parse_rule_to_dict(rule), ensure_ascii=False, indent=2)
    content_preview = ""
    tail_preview = ""
    if fc and fc.sheets and any(s.rows for s in fc.sheets):
        content_preview = _prepare_content_for_ai(fc)
        tail_preview = _prepare_tail_for_ai(fc)

    file_section = ""
    if content_preview:
        file_section = f"""## 文件内容（前300行）
```
{content_preview}
```

## 文件尾部（最后30行）
```
{tail_preview}
```
"""

    user_prompt = f"""用户对当前规则提出了修改意见，请根据反馈调整规则。

## 用户的修改要求
{feedback}

## 当前规则
```json
{rule_json_str}
```

{file_section}
请按用户要求调整规则，输出完整的规则JSON。注意：
1. 保留原规则的id（{rule.id}）
2. 只修改用户要求的部分，不要改动其他正常工作的配置
3. 如果用户说某个字段不生效，检查映射是否正确
4. 如果用户说数据不正确，检查行号、列号是否正确"""

    resp = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.1,
        max_tokens=4096,
        response_format={"type": "json_object"},
    )
    result = _parse_response(resp)
    result.rule.id = rule.id
    return result


def _parse_response(resp) -> AIRuleGenerationResult:
    content = resp.choices[0].message.content if resp.choices else ""
    if not content:
        raise ValueError("DeepSeek API 返回空响应")
    parsed = json.loads(content)
    rule = parse_rule_from_dict(parsed.get("rule", {}))
    if not rule.id:
        import time
        rule.id = f"rule_{int(time.time() * 1000)}"
    return AIRuleGenerationResult(
        rule=rule,
        confidence=parsed.get("confidence", 0.5),
        reasoning=parsed.get("reasoning", ""),
        uncertain_mappings=parsed.get("uncertainMappings", []),
        file_analysis=parsed.get("fileAnalysis", ""),
    )
