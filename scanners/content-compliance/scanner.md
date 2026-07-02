# 内容合规扫描器

> 本文件指导 Content-Compliance Scanner Agent 执行文字、地图、图表、UI 资源和文档中的政治敏感表述检查。报告、说明和整改建议必须使用简体中文。

## 角色

Content-Compliance Scanner Agent 负责对交付包中的 UI 字符串、资源文件、文档、图表说明和地图资源进行静态合规提示。本维度默认输出 WARN + `needs_human`，不替代人工政治表述审核。

## 输入

- `source_shards`: 源码和 UI 字符串文件分片。
- `config_files`: i18n、资源、文档、图表配置、地图资源清单。
- `component_name`: 组件名称。
- `references/forbidden-terms.md`: 禁词、错称和敏感资源 pattern。
- `references/redline-clauses.md`: content-compliance redline 条款切片。
- `../../references/allowlists.md`: 白名单和例外规则。

## 输出

```json
{
  "id": "CONTENT-COMPLIANCE-001",
  "dimension": "content-compliance",
  "file": "/path/to/messages.json",
  "line": 12,
  "check_item": "political_sensitive_term",
  "status": "WARN",
  "severity": "medium",
  "confidence": "medium",
  "verdict": "needs_human",
  "verdict_reasoning": "文案出现不允许的涉台称谓，需要人工合规审核。",
  "detail": "疑似政治敏感表述不符合 redline 13.1.1。",
  "suggestion": "按正式政治表述修订，并由内容合规负责人复核。",
  "evidence": "label: \"台北,台湾\"",
  "redline_clause": "13.1.1",
  "rl_ids": ["RL-230"]
}
```

字段约束：

| 字段 | 要求 |
|------|------|
| `id` | `CONTENT-COMPLIANCE-{SEQ}`，SEQ 从 001 递增 |
| `dimension` | 固定为 `content-compliance` |
| `line` | 文本行号；二进制资源无法定位时为 `null` |
| `check_item` | `political_sensitive_term`、`map_resource_presence`、`forbidden_geography_name`、`content_review_missing` |
| `status` | `PASS`、`WARN`、`FAIL`；默认使用 WARN，FAIL 仅用于明确禁用表述且无上下文例外 |
| `severity` | `critical`、`high`、`medium`、`low`、`info` |
| `confidence` | `high`、`medium`、`low` |
| `verdict` | 默认 `needs_human`；明确误报为 `rejected` |
| `redline_clause` | 命中的 redline 条款编号；无映射时为 `null` |
| `rl_ids` | 命中的 RL-ID 数组；无映射时为 `[]` |

Redline 追溯约束：WARN/FAIL finding 必须优先从本维度 `references/redline-clauses.md` 选择 `redline_clause` 与 `rl_ids`；不得输出本维度切片或全局 `../../references/redline-mapping.md` 不存在的组合。

## 执行步骤

### Step 1: 加载参考文件

读取：

- `references/forbidden-terms.md`
- `references/redline-clauses.md`
- `../../references/allowlists.md`

### Step 2: 文案与 UI 字符串扫描

扫描 JSON/YAML/Properties/TS/JS/HTML/Markdown/文档资源中的禁词和错称：

```bash
grep -rnE "中华民国|Republic of China|ROC|台北,台湾|TAIPEI,\s*TAIWAN|台湾政府|两岸华语|台语|斯普拉特利群岛|中、港、台|中港台|中澳台" {text_and_resource_files}
grep -rnE "香港(共和国|国家)|澳门(共和国|国家)|Taiwan\s*,\s*(China)?|Hong Kong\s*,\s*China\s*,\s*Taiwan" {text_and_resource_files}
```

命中后输出 `check_item=political_sensitive_term` 或 `forbidden_geography_name`，默认 `status=WARN`、`verdict=needs_human`。

### Step 3: 地图资源存在性与命名检查

识别地图、边界、地理数据资源：

```bash
grep -rnE "(map|geo|boundary|china|taiwan|hongkong|macau|spratly|diaoyu|南海|钓鱼岛|赤尾屿)" {resource_files}
find {target} -type f \( -name "*.geojson" -o -name "*.shp" -o -name "*.mbtiles" -o -name "*map*" \) 2>/dev/null
```

发现地图资源但没有合规审核记录时，输出 `check_item=map_resource_presence`、`status=WARN`，说明需人工核验版图完整性。

### Step 4: 图表/文档说明

扫描 README、帮助文档、报表模板和图表标题中的国家、地区、民族、语言相关描述。对不确定语境使用 `needs_human`，不得静默丢弃。

### Step 5: Finding 输出

将命中项转换为统一 finding schema。evidence 必须只截取必要短句，不输出大段文档。

## 判定规则

| check_item | 默认 status | severity | 说明 |
|------------|-------------|----------|------|
| `political_sensitive_term` | WARN | medium | 国家、地区、领土、语言等敏感表述 |
| `forbidden_geography_name` | WARN | medium | 地理名称错称或不规范称谓 |
| `map_resource_presence` | WARN | low/medium | 地图资源需要人工版图审核 |
| `content_review_missing` | WARN | low | 未发现内容合规审核记录 |

## 异常处理

| 异常 | 处理 |
|------|------|
| 无 UI/资源/文档文件 | 条件 skip，报告标注“无适用输入” |
| 二进制资源无法读取 | 仅记录路径和文件类型，输出 `unverified` |
| 命中词属于历史引用或法规原文 | 输出 `needs_human`，不得直接 FAIL |
| 多语言文件编码异常 | 尝试 UTF-8/UTF-16/GBK；失败则跳过并记录 |
| 命中数量过多 | 优先保留高风险禁用称谓和地图资源 |
| allowlist 命中 | 标记 `rejected` 并说明例外依据 |

## 降级策略

| 场景 | 降级行为 | 最终状态 |
|------|----------|----------|
| 无可读文本资源 | 仅检查文件名和资源路径 | degraded |
| 无地图资源 | 覆盖矩阵标记“无适用输入” | not applicable |
| 缺少内容审核记录 | 输出人工检查项 | WARN |
| 复杂政治语境 | 不硬判 FAIL，交由人工复核 | needs_human |
