# Phase 3: 报告生成指令

> 本文件指导 Reporter Agent 汇总裁决后的 findings，生成终端摘要、JSON 结构化数据、综合 Markdown 报告和四份维度专项报告。

## 角色

Reporter Agent 负责把 Verdict 阶段输出转换为可审计报告。报告必须使用简体中文，必须保留数据来源、裁决结果、质量审计结果和降级输出说明。

## 输入

- 所有裁决后的 findings（JSON 数组）。
- Scan Plan 元数据：`component_name`、`target_path`、`total_files`、`scan_files`、`excluded_files`、`elf_count`、`source_count`、`config_count`、`duration`。
- Verdict 汇总：按 `severity`、`dimension`、`verdict` 聚合后的统计。
- 审计日志：`failed_agents`、`retried_agents`、`degraded_dimensions`、`rejected_findings`、`needs_human_findings`、`unverified_findings`。
- 报告模板：`templates/` 目录下的综合模板和四份专项模板。

## 输出

### 1. 终端摘要

终端摘要用于实时反馈扫描结果，应包含：

- 扫描目标、组件名称、扫描耗时。
- 各阶段状态：Pre-flight、Recon、Scan、Verdict、Report。
- 严重度统计：`critical`、`high`、`medium`、`low`、`info`。
- 裁决统计：`confirmed`、`suspected`、`rejected`、`needs_human`、`unverified`。
- 生成文件路径和降级状态。

### 2. JSON 结构化数据

输出文件：`security-scan-report-{component_name}-{date}.json`

JSON 必须包含以下顶层字段：

- `scan_metadata`: 版本、时间、目标、扫描文件数、耗时和 scanner 版本。
- `summary`: 按严重度、维度和裁决结果聚合的统计。
- `findings`: 所有非静默丢弃的 findings。`rejected` 可保留在 JSON 中，但正式问题清单必须能区分。
- `audit_log`: 覆盖率、失败 agent、重试 agent、降级维度和审计警告。
- `report_audit`: 字段完整性、数据一致性、内容质量和覆盖完整性审计结果。

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
  "evidence": "RELRO: Partial RELRO\nStack: Canary found\nNX: NX disabled"
}
```

字段缺失时不得生成看似完整的 JSON；应进入降级流程并在 `report_audit` 中标记。

### 2.1 组件档案 Summary JSON

输出文件：`component-info-summary-{component_name}-{date}.json`

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

输出文件：`security-scan-report-{component_name}-{date}.md`

使用 `templates/report-comprehensive.md` 填充数据。综合报告必须包含：

- 基本信息和扫描统计。
- 严重度汇总和各维度发现统计。
- 六个维度的详细发现：ELF、公网地址、口令和硬编码、未公开接口、敏感文件泄露、文件权限。
- 审计日志、质量审计结果和降级输出说明。

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

- [密码学详细 finding](./report-密码学-{name}-{date}.md)
- [网络协议与端口详细 finding](./report-网络-{name}-{date}.md)
- [组件档案详细 finding](./report-组件档案-{name}-{date}.md)

### 声明 vs 实际

| 类别 | 声明 | 实际 | 一致 |
| 协议 | {self_declared.protocols} | {actual.protocols} | {yes/no} |
| 算法 | {self_declared.algorithms} | {actual.algorithms} | {yes/no} |
```

数据来源：`component-info-summary-{name}-{date}.json`。

### 4. 七份维度专项报告

所有专项报告使用简体中文，并使用对应模板：

- `templates/report-安全编译.md` -> `report-安全编译-{component_name}-{date}.md`
- `templates/report-公网地址.md` -> `report-公网地址-{component_name}-{date}.md`
- `templates/report-口令硬编码.md` -> `report-口令硬编码-{component_name}-{date}.md`
- `templates/report-未公开接口.md` -> `report-未公开接口-{component_name}-{date}.md`
- `templates/report-密码学.md` -> `report-密码学-{component_name}-{date}.md`
- `templates/report-网络.md` -> `report-网络-{component_name}-{date}.md`
- `templates/report-组件档案.md` -> `report-组件档案-{component_name}-{date}.md`

专项报告只展示对应维度的数据，但必须继承 JSON 中的裁决结果、严重度和审计状态。

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
3. 生成 JSON 结构化数据并校验 schema。
4. 渲染综合 Markdown 报告。
5. 渲染四份维度专项报告。
6. 执行 A3 报告内容审计。
7. 根据审计结果输出正式报告、WARN 报告或降级报告。
