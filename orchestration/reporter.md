# Phase 3: 报告生成指令

> 本文件指导 Reporter Agent 汇总裁决后的 findings，生成终端摘要、JSON 结构化数据、综合 Markdown 报告和 13 份维度独立详细 Markdown 报告。

## 角色

Reporter Agent 负责把 Verdict 阶段输出转换为可审计报告。报告必须使用简体中文，必须保留数据来源、裁决结果、质量审计结果和降级输出说明。

## 输入

- 所有裁决后的 findings（JSON 数组）。
- Scan Plan 元数据：`component_name`、`target_path`、`total_files`、`scan_files`、`excluded_files`、`elf_count`、`source_count`、`config_count`、`duration`。
- Verdict 汇总：按 `severity`、`dimension`、`verdict` 聚合后的统计。
- 审计日志：`failed_agents`、`retried_agents`、`degraded_dimensions`、`rejected_findings`、`needs_human_findings`、`unverified_findings`。
- Redline 映射：`references/redline-mapping.md`，用于 A3b 覆盖矩阵和人工检查清单。
- 报告模板：`templates/report-manifest.yaml` 声明的综合模板和全部维度模板。
- 报告维度清单：`reporting_dimensions = templates/report-manifest.yaml 中全部 13 个维度`。这是 Phase 3 报告产物数量和命名的唯一来源。
- 执行维度清单：`executed_dimensions`，只表示 Phase 1 实际扫描执行结果，包括实际执行、条件跳过、profile 跳过、工具缺失、降级或失败状态；它不得决定 Phase 3 维度报告文件数量。
- 口径约束：executed_dimensions 只表示 Phase 1 实际扫描执行结果；reporting_dimensions 才决定 Phase 3 维度报告产物。

`scan_profile` 只影响扫描调度强度，不影响最终 13 份维度独立详细报告产物数量。无论使用 Claude Code / Codex / OpenCode，Reporter 都必须遵循同一共享报告契约。

报告口径：scan_profile 只影响扫描调度强度，不影响最终 13 份维度独立详细报告产物数量。

Phase 3 的固定 Markdown 产物契约是：综合 Markdown 报告 + JSON 结构化数据 + 13 份维度独立详细 Markdown 报告。

## 输出

### 1. 终端摘要

终端摘要用于实时反馈扫描结果，应包含：

- 扫描目标、组件名称、扫描耗时。
- 各阶段状态：Pre-flight、Recon、Scan、Verdict、Report。
- 严重度统计：`critical`、`high`、`medium`、`low`、`info`。
- 裁决统计：`confirmed`、`suspected`、`rejected`、`needs_human`、`unverified`。
- 生成文件路径和降级状态。

### 2. JSON 结构化数据

输出文件：`security-reports/security-scan-report-{component_name}-{date}.json`

JSON 必须包含以下顶层字段：

- `scan_metadata`: 版本、时间、目标、扫描文件数、耗时和 scanner 版本。
- `summary`: 按严重度、维度和裁决结果聚合的统计。
- `findings`: 所有非静默丢弃的 findings。`rejected` 可保留在 JSON 中，但正式问题清单必须能区分。
- `audit_log`: 覆盖率、失败 agent、重试 agent、降级维度和审计警告。
- `report_audit`: 字段完整性、数据一致性、内容质量和覆盖完整性审计结果。
- `redline_coverage`: 40 条 redline 条款覆盖矩阵，来源于 `references/redline-mapping.md`。

每条 finding 必须包含：

```json
{
  "id": "ELF-001",
  "dimension": "elf",
  "file": "/path/to/binary",
  "line": null,
  "check_item": "nx",
  "status": "FAIL",
  "severity": "high",
  "confidence": "high",
  "verdict": "confirmed",
  "verdict_reasoning": "checksec 明确显示 NX disabled，属于确定性二进制安全编译问题。",
  "detail": "NX bit not set, stack is executable",
  "suggestion": "Add -Wl,-z,noexecstack to linker flags",
  "evidence": "RELRO: Partial RELRO\nStack: Canary found\nNX: NX disabled",
  "redline_clause": "11.2.1",
  "rl_ids": ["RL-260"]
}
```

字段缺失时不得生成看似完整的 JSON；应进入降级流程并在 `report_audit` 中标记。

### 2.1 组件档案 Summary JSON

输出文件：`security-reports/component-info-summary-{component_name}-{date}.json`

这是新维度的双产出之一，结构按 9 字段聚合，便于生成 Markdown "组件档案概览" 章节。

JSON 顶层字段：

```json
{
  "version": "1.0",
  "component": "...",
  "scan_date": "...",
  "architecture": {"value": "B/S", "confidence": "high", "label": "AUTO", "inference_note": "...", "reverse_evidence": [...]},
  "protocols": [{"name": "TLSv1.3", "evidence": "..."}],
  "ports": [{"port": 443, "protocol": "TCP", "evidence": "..."}],
  "symmetric_algos": [...],
  "asymmetric_algos": [...],
  "hash_algos": [...],
  "custom_algos": [...],
  "pseudo_encryption": [...],
  "random_sources": [...],
  "default_accounts": [...],
  "personal_data": [...],
  "requires_root": {"value": "否", "confidence": "high", "label": "AUTO", "inference_note": "...", "reverse_evidence": [...]},
  "self_declared": {"algorithms": [...], "protocols": [...], "matched_actual": true, "mismatches": []},
  "dependency_summary": {"tier1_libraries": 12, "tier2_libraries": 5, "libraries_with_red_line": 2, "missing_lock_file": false},
  "red_line_violations": [{"rule_id": "RL-002", "category": "insecure_hash", "severity": "high", "summary": "...", "findings": ["CRYPTO-001"]}],
  "needs_human": ["INFO-001"]
}
```

每条 finding 的 `red_line_finding` 字段值必须能在 `findings` 数组中找到对应 id。

### 3. 综合 Markdown 报告

输出文件：`security-reports/security-scan-report-{component_name}-{date}.md`

使用 `templates/report-comprehensive.md` 填充数据。综合报告必须包含：

- 基本信息和扫描统计。
- 严重度汇总和各维度发现统计。
- 全部 13 个报告维度的详细发现与对应独立详细报告索引。
- `reporting_dimensions` 对应的维度状态摘要和独立详细报告索引；状态可来自 `executed_dimensions`，但缺失维度必须补为 `missing_profile_dimension`。
- Redline 40 条覆盖矩阵与人工合规项附录。
- 审计日志、质量审计结果和降级输出说明。

`dimension_report_index` 必须列出 13 个维度独立详细报告路径。`dimension_status_summary` 必须列出 13 个维度状态。每个维度详细区块没有 finding 时必须填写“未发现问题”或“不适用/降级原因：{reason}”，不得空缺。

### 3.1 综合报告"组件档案概览"章节

综合报告顶部（基本信息和扫描统计之后）插入"组件档案概览"章节：

```markdown
## 组件档案概览

| 字段 | 值 | 标签 | 备注 |
|------|-----|------|------|
| 架构类型 | {architecture.value} | {architecture.label} | {architecture.inference_note} |
| 通信协议 | {protocols.names} | AUTO | - |
| ... (其他 7 个字段) |

### 子报告索引

- [密码学详细 finding](./security-reports/report-密码学-{name}-{date}.md)
- [网络协议与端口详细 finding](./security-reports/report-网络-{name}-{date}.md)
- [组件档案详细 finding](./security-reports/report-组件档案-{name}-{date}.md)

### 声明 vs 实际

| 类别 | 声明 | 实际 | 一致 |
| 协议 | {self_declared.protocols} | {actual.protocols} | {yes/no} |
| 算法 | {self_declared.algorithms} | {actual.algorithms} | {yes/no} |
```

数据来源：`component-info-summary-{name}-{date}.json`。

### 3.2 Redline 覆盖矩阵与人工合规项

Reporter 必须根据 `references/redline-mapping.md` 生成综合报告附录：

| 字段 | 说明 |
|------|------|
| `clause_id` | redline 条款编号 |
| `automation` | `full` / `partial` / `manual` |
| `profile_min` | 最低适用 profile |
| `scanner_dims` | 自动/半自动主责维度；manual 项为空 |
| `finding_ids` | 命中的 confirmed/suspected finding ID；无命中时写明“未发现问题”或“无适用输入” |
| `manual_note` | manual 或 partial 项的人工复核说明 |
| `coverage_status` | `covered` / `no finding` / `manual` / `degraded` / `not applicable` |

统计口径：

- manual 项只进入“redline 人工合规项”附录，不计入 automated FAIL 总数。
- partial 项若没有可自动确认的 finding，必须保留人工复核说明。
- `needs_human` 和 `unverified` 不得计入 confirmed 问题总数，但必须在覆盖矩阵中可追溯。
- 40 条条款必须全部出现；缺失任一条为 A3b FAIL。
- `redline_manual_checklist` 必须由 `automation=manual` 条款生成，字段至少包含 clause、manual_note、建议责任方和状态。

### 4. 维度专项报告

所有专项报告使用简体中文，并使用 `templates/report-manifest.yaml` 中的对应模板生成独立详细报告：

- `templates/report-安全编译.md` -> `security-reports/report-安全编译-{component_name}-{date}.md`
- `templates/report-公网地址.md` -> `security-reports/report-公网地址-{component_name}-{date}.md`
- `templates/report-口令硬编码.md` -> `security-reports/report-口令硬编码-{component_name}-{date}.md`
- `templates/report-未公开接口.md` -> `security-reports/report-未公开接口-{component_name}-{date}.md`
- `templates/report-敏感文件泄露.md` -> `security-reports/report-敏感文件泄露-{component_name}-{date}.md`
- `templates/report-文件权限.md` -> `security-reports/report-文件权限-{component_name}-{date}.md`
- `templates/report-密码学.md` -> `security-reports/report-密码学-{component_name}-{date}.md`
- `templates/report-网络.md` -> `security-reports/report-网络-{component_name}-{date}.md`
- `templates/report-组件档案.md` -> `security-reports/report-组件档案-{component_name}-{date}.md`
- `templates/report-依赖与漏洞.md` -> `security-reports/report-依赖与漏洞-{component_name}-{date}.md`
- `templates/report-安全编码.md` -> `security-reports/report-安全编码-{component_name}-{date}.md`
- `templates/report-完整性.md` -> `security-reports/report-完整性-{component_name}-{date}.md`
- `templates/report-内容合规.md` -> `security-reports/report-内容合规-{component_name}-{date}.md`

Reporter 必须为 `reporting_dimensions` 中全部 13 个维度生成独立详细报告。专项报告只展示对应维度的数据，但必须继承 JSON 中的裁决结果、严重度和审计状态。综合报告必须提供全部 13 份独立详细报告的索引。

未实际执行的维度也必须生成占位详细报告：

- `skipped_by_profile`：scan_profile 未调度该维度。报告必须写明 profile 名称、未调度原因、仍生成占位报告的依据。
- `skipped_by_condition`：目标输入不满足维度扫描条件。报告必须写明输入条件、判定证据和不适用范围。
- `degraded`：工具缺失、输入物化失败或降级路径生效。报告必须写明降级路径、受影响检查项和审计引用。
- `failed`：scanner 执行失败或重试后仍失败。报告必须写明失败原因、重试记录、保留的部分结果和人工复核建议。
- `missing_profile_dimension`：`executed_dimensions` 未提供该维度状态。报告必须写明这是状态缺口，并在 A3c 中记录为审计问题。

占位报告中的问题表无 finding 时填写“未发现问题”或“不适用/降级原因：{reason}”，质量审计结果和降级输出说明仍必须完整。

### 5. 报告完整性检查

所有预期输出文件生成后，必须执行完整性检查：

1. 根据 `templates/report-manifest.yaml` 列出所有预期输出文件：
   - 汇总报告：`security-reports/security-scan-report-{component_name}-{date}.md`
   - JSON 数据：`security-reports/security-scan-report-{component_name}-{date}.json`
   - 组件档案 JSON：`security-reports/component-info-summary-{component_name}-{date}.json`
   - 维度专项报告：`security-reports/report-{dim_display_name}-{component_name}-{date}.md`（`reporting_dimensions` 全部 13 个维度）
2. 逐一检查各文件是否存在。
3. 若任一预期文件缺失，重新执行对应报告生成逻辑（重新渲染并写入）。
4. 重试最多 2 次。仍缺失则记录到降级输出说明。

### 5.1 A3c 报告产物清单审计

- `reporting_dimensions` 必须等于 `templates/report-manifest.yaml` 中全部 13 个维度；每个维度必须存在模板和唯一输出路径。
- A3c 必须检查“综合报告 + JSON + 13 个维度报告”是否全部存在；缺任一维度报告即 A3c FAIL。
- `dimension_report_index 必须覆盖 13 个维度`，且每个索引路径必须指向实际生成文件。
- `dimension_status_summary 必须覆盖 13 个维度`，且每个维度必须有状态、原因、输入条件、降级路径或审计引用。
- `实际文件清单必须覆盖 13 个维度`，并与 `templates/report-manifest.yaml` 输出路径一致。
- `executed_dimensions` 中每个维度必须能映射到 `templates/report-manifest.yaml`；不在 `executed_dimensions` 中的 manifest 维度必须补为 `missing_profile_dimension`。
- 缺少任一独立详细报告、索引缺失、状态摘要缺维度或实际文件清单缺维度均为 A3c FAIL。

## 渲染规则

- 所有模板占位符必须被实际内容替换。
- 没有数据的字段填写“`不适用：{reason}`”，不得使用空字符串、`-`、`N/A` 或单独的“无”。
- 表格行中的管道符、换行和敏感内容必须转义或脱敏，避免破坏 Markdown。
- 口令和硬编码报告中的密钥值必须最小必要脱敏。
- `rejected` finding 不进入正式问题表格，但要进入审计日志或例外场景统计。
- `needs_human` 和 `unverified` finding 必须在报告中清晰标注，不得混入 confirmed 数量。

## 报告内容审计（Audit Checkpoint A3）

生成报告后，Orchestrator 执行内容审计。Reporter 必须根据审计结果修正或降级输出。

### 字段完整性审计

- 所有模板定义的表头列都必须存在。
- 每行每个字段必须非空。
- 不允许使用 `-`、`N/A`、空字符串或单独的“无”作为占位符。
- 确实无数据时，必须填写“`不适用：{reason}`”。
- 任何必填字段缺失均为 FAIL。

### 数据一致性审计

- “问题汇总”数量必须等于结果表格实际问题数。
- “扫描文件数”必须等于 Recon Scan Plan 中的实际文件数。
- 各维度报告 findings 总数必须与 JSON 数据中对应维度 findings 总数一致。
- 综合报告严重度汇总必须与 JSON `summary.by_severity` 一致。
- `confirmed`、`suspected`、`needs_human`、`unverified`、`rejected` 的统计口径必须在 JSON、综合报告和专项报告中一致。

### 内容质量审计

- “说明”字段至少 10 个汉字，且不能是模板文字。
- “修复建议”必须针对具体问题，不能只写通用整改口号。
- “是否需要整改”必须明确填写“是”或“否”。
- 未公开接口的“涉及功能描述”必须可从 evidence 或上下文追溯。
- ELF 修复建议必须包含具体编译、链接或构建配置方向。
- 质量不达标为 WARN，报告末尾必须附加“[审计备注] 部分字段需人工补充”。

### 覆盖完整性审计

- 所有 `confirmed` 和 `suspected` findings 必须出现在对应专项报告或综合报告详细发现中。
- `needs_human` 和 `unverified` findings 必须出现在报告的人工确认或降级说明中。
- `rejected` findings 必须出现在审计日志或例外清单中。
- 对比 JSON 数据和 Markdown 报告，遗漏数大于 0 为 FAIL。

### Redline 覆盖矩阵审计（A3b）

- `redline_coverage` 必须覆盖 mapping 中全部 40 条 `clause_id`。
- automated/partial 项不得与 manual 项重复计数。
- 每条 automated/partial 的 `finding_ids`、`coverage_status` 或降级原因必须与 findings/audit_log 可追溯。
- 每条 manual 的 `manual_note` 必须进入人工合规项附录。
- 覆盖矩阵缺项、重复条款、状态与 findings 不一致均为 FAIL。

### 报告产物清单审计（A3c）

- `reporting_dimensions` 必须与 `templates/report-manifest.yaml` 全部 13 个维度一致。
- `templates/report-manifest.yaml` 是维度模板、输出命名和 13 份维度报告清单的唯一来源。
- `dimension_report_index`、`dimension_status_summary` 和实际文件清单必须同时覆盖 13 个维度。
- 独立详细报告缺失、维度状态无说明或索引指向不存在文件均为 FAIL；最多重试 2 次，仍失败则报告状态必须标记为 `blocked` 或 `degraded`。

## 审计失败处理

| 审计结果 | 处理 |
|----------|------|
| PASS | 正常输出报告 |
| WARN | 输出报告，并在报告末尾附加“[审计备注] 部分字段需人工补充” |
| FAIL | 将缺失或错误信息反馈给 Reporter Agent，重新生成报告，最多 2 次 |
| 重试后仍 FAIL | 降级输出，并附加“[审计警告] 以下字段缺失：...” |

降级输出不得丢弃已确认结果。必须明确列出：

- 降级原因。
- 受影响维度。
- 缺失字段或不一致统计。
- 已保留的 findings 范围。
- 需要人工补充或复核的事项。

## 异常处理

| 异常 | 处理 |
|------|------|
| findings 数据不完整 | 生成部分报告，标记 “DATA INCOMPLETE”，列出缺失字段 |
| Markdown 渲染失败 | 降级为纯文本报告，保留同等字段内容 |
| JSON schema 校验失败 | 修复后重新生成，最多 2 次 |
| 输出文件写入失败 | 改为终端直接输出 JSON，并标记写入失败 |
| 模板文件缺失 | 输出阻断错误，列出缺失模板，不生成伪造报告 |
| 审计统计不一致 | 重新聚合统计并重新渲染；仍失败时降级输出 |

## 生成顺序

1. 校验输入 findings 和 Scan Plan 元数据。
2. 聚合 summary 和 audit_log。
3. 根据 `references/redline-mapping.md` 构造 `redline_coverage`。
4. 生成 JSON 结构化数据并校验 schema。
5. 渲染综合 Markdown 报告（含 A3b 覆盖矩阵和人工合规项）。
6. 按 `reporting_dimensions` 渲染全部 13 份维度独立详细报告。
7. 执行报告完整性检查（§5）；缺失则重新生成对应报告，最多 2 次。
8. 执行 A3/A3b/A3c 报告内容审计。
9. 根据审计结果输出正式报告、WARN 报告或降级报告。
