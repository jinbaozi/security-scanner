# Orchestrator 编排指令

> 本文件定义 Orchestrator 的 Phase 调度逻辑、审计检查点和错误处理策略。

## 整体流程

```text
Phase -1: Pre-flight Check -> 审计 -> Phase 0: Recon -> 审计 A0
-> Phase 1: Registry Scheduling -> Phase 1.5: Scanner Sessions -> 审计 A1 -> Phase 2: Verdict -> 审计 A2
-> Phase 3: Report -> 审计 A3 -> 输出
```

## Phase 调度规则

## 输入参数

Orchestrator 必须接收以下输入：

| 参数 | 必填 | 默认值 | 说明 |
|------|------|--------|------|
| `target_path` | 是 | 无 | 待扫描目标路径 |
| `scan_profile` | 否 | `kylin-redline-p0` | 扫描 profile，决定 Phase 1 可调度维度 |

合法 `scan_profile` 仅包括：

- `kylin-redline-p0`：`elf`、`url`、`secret`、`comment`、`fileleak`、`permission`、`crypto`、`network`、`component-info`、`dependency`
- `kylin-redline-full`：全部已定义 13 维（`elf`、`url`、`secret`、`comment`、`fileleak`、`permission`、`crypto`、`network`、`component-info`、`dependency`、`secure-coding`、`integrity`、`content-compliance`）
- `kylin-redline-binary`：`elf`、`fileleak`、`permission`、`dependency`

未提供 `scan_profile` 时使用 `kylin-redline-p0`。`kylin-redline-full` 必须显式指定，不作为默认值。任何不在合法列表中的 `scan_profile` 都必须立即 `FAIL`，输出错误并停止后续 Phase。

## 终端摘要格式

每个 Phase 完成后输出终端摘要，格式参见 `SKILL.md` 的执行流程示例。Phase 3 完成后输出完整扫描结果摘要，格式参见 `orchestration/reporter.md`。

### 顺序执行

Phase -1 和 Phase 0 必须顺序执行，前一 Phase 完成后才能进入下一 Phase。

### Phase 1：注册表加载与拓扑调度

Phase 1 不再枚举固定 scanner 文件路径，也不写死 9 维。Orchestrator 必须先校验 `scan_profile`，再通过 `scanners/registry/` 提供的 registry API 加载生产布局：调用 `discover_scanners(Path("scanners"))` 发现 scanner 元数据和 prompt；取得 profile 允许维度集合；计算 `selected_scanners = discovered_scanners ∩ profile_dimensions`；对 `selected_scanners` 调用 `topological_order(selected_scanners)` 生成依赖优先的执行顺序，并确认不存在循环依赖；随后初始化 `ScanContext()` 作为本次扫描中 scanner findings 的唯一交换上下文。

调度状态必须区分：

- `scheduled_dimensions`：被 registry 发现且被 profile 选中的维度。
- `skipped_by_profile`：被 registry 发现但不在当前 profile 中的维度，不计入失败。
- `missing_profile_dimensions`：profile 声明但 registry 未发现的维度，记录为本次 profile 覆盖缺口；若该缺口影响 profile 的必检目标，Phase 1 审计应给出 `WARN` 或 `FAIL`。
- `skipped_by_condition`：profile 选中且 registry 可发现，但因输入类型不适用而跳过的维度，必须记录具体条件和降级 finding。

### Phase 1.5：启动各 scanner session

Orchestrator 按 `selected_scanners` 的拓扑顺序启动 scanner。每个 scanner 必须运行在独立 LLM session 中（Q21B），只读取自身目录下的 `meta.yaml` session 配置与 `scanner.md` system prompt。对每个 `meta.consumes` 条目，调用 `context.consume(dim, severity_filter, token_budget)` 取得上游 findings；这些 consumed finding JSON 必须作为 user message 中的数据块附加给下游 scanner，不能写入 system prompt（Q29）。按 `meta.references` 加载 reference 文件并纳入该 session 的用户上下文；scanner 输出后解析 finding JSON，并调用 `context.publish(scanner_id, findings)` 发布本维度结果。

### Phase 2：裁决输入

Phase 2 必须调用 `context.all_findings()` 从 `ScanContext` 收集所有已发布维度的 findings，再进入现有 verdict flow。裁决阶段继续负责跨维度去重、补充 `confidence` 与 `verdict_reasoning`、执行 A2 审计，并保持后续报告流程不变。

### 条件跳过

| 条件 | 影响维度 | 行为 |
|------|----------|------|
| 维度不在当前 `scan_profile` 中 | 任意维度 | 记录 `skipped_by_profile`，不启动 scanner，不计入失败。 |
| 维度在 profile 中但 registry 未发现 | 任意维度 | 记录 `missing_profile_dimensions`；A1/A1b 按 profile 必检目标判定 WARN 或 FAIL。 |
| `elf_files` 为空 | `elf` | 记录 `skipped_by_condition`，不启动 ELF Scanner。 |
| `source_shards` 为空 | `url`, `secret`, `comment`, `crypto`, `network`, `component-info`, `secure-coding`, `content-compliance` | 跳过源码侧能力；若维度还有 config/manifest 输入，可仅降级相关检查项。 |
| `config_files` 为空 | `secret`, `url`, `crypto`, `network`, `component-info`, `dependency`, `integrity`, `content-compliance` | 跳过配置/声明扫描能力，记录降级原因。 |
| `docker_files` 为空 | `component-info` | root 启动信号降级为单源 INFERRED。 |
| `dependency_files` 为空 | `dependency` 主责；`crypto`, `network` 受影响 | Dependency Scanner 产出 `MISSING_LOCK_FILE` WARN finding；Crypto/Network 不重复产出该 finding，仅跳过依赖版本增强能力。 |
| 无 C/C++ 源码 | `secure-coding` | 记录条件跳过；若存在其他源码语言，可仅执行通用注释/脚本 pattern。 |
| 非 RPM/DEB 且无构建/安装脚本 | `integrity` | 记录 `needs_human` / `unverified` 降级项，不硬判 FAIL。 |
| 无 UI、资源、文档文件 | `content-compliance` | 记录条件跳过；报告覆盖矩阵标为“无适用输入”。 |
| 对应依赖不可用且无降级方案（或用户已拒绝降级） | 任意维度 | 跳过该维度，记录 `degraded_dimensions`。 |

## 审计检查点

### 三级处理

```text
PASS -> 进入下一 Phase
WARN -> 记录警告，继续执行，并在最终报告中标注
FAIL -> 进入修复循环（最多 2 次自动修复）-> 仍失败则降级
```

### A0（Recon 审计）

- 覆盖率 >= 90%：PASS。
- 覆盖率 80-90%：WARN。
- 覆盖率 < 80%：FAIL。
- 分片超限：FAIL。

### A0b（Redline Profile 输入审计）

- `scan_profile` 非法：FAIL，列出合法值并停止进入 Phase 1。
- profile 所需输入已识别：PASS。
- 缺少可选输入（如 `communication_matrix_path`）：WARN，记录降级路径并继续。
- 缺少必需输入且无降级路径：FAIL。

### A1（Scan 审计）

- 所有入选 Scanner 完成且输出符合 schema：PASS。
- `missing_profile_dimensions` 为空或仅影响非必检能力：PASS/WARN，需在最终报告标注。
- `missing_profile_dimensions` 影响当前 profile 必检目标：FAIL。
- 1 个 Scanner 失败：WARN，重试失败项（最多 2 次）。
- 2-3 个 Scanner 失败：部分降级，继续其他维度。
- 失败维度数超过当前 profile 可调度维度数的 30%：FAIL，Phase 级降级，收集已完成结果。

### A1b（Redline 维度执行/Skip 审计）

- profile 声明维度均处于 `scheduled_dimensions`、`skipped_by_profile`、`skipped_by_condition`、`missing_profile_dimensions` 或 `degraded_dimensions` 之一：PASS。
- 任一 profile 维度没有执行结果且没有 skip/degraded 原因：WARN；若影响必检目标则 FAIL。
- `degraded_dimensions` 必须包含 `dimension`、`reason`、`fallback`、`audit_log_ref`。

### A1b+（Context Consumes 截断审计）

- 任一 `context.consume()` 因 `token_budget` 截断时，必须在 `audit_log` 记录上游维度、过滤条件、原始数量、注入数量和截断策略。
- 高严重度 findings 必须优先保留；截断未记录为 WARN。

### A2（Verdict 审计）

- 所有裁决包含 `confidence` 和 `verdict_reasoning`：PASS。
- 部分缺失：WARN，重新补充。
- 大面积缺失：FAIL，标记为 `unverified`。

### A2b（Redline 去重与追溯审计）

- 每条 `FAIL` / `WARN` finding 应包含 `redline_clause` 或可追溯的 `rl_ids`；缺少少量字段为 WARN，大面积缺失为 FAIL。
- `crypto` 与 `secret` 共享同一凭证字符串时，`secret` 优先；`crypto` 仅保留算法/协议类 finding。
- `MISSING_LOCK_FILE` 仅由 `dependency` 主责产出；Crypto/Network 不重复产出。
- `secret` 与 `fileleak` 同时命中认证密钥路径时，文件泄露/权限路径证据优先保留，源码凭据 finding 合并为补充 evidence。
- `secure-coding` 负责注释包裹代码，`comment` 负责注释描述隐藏接口，不重复报告同一注释块。

### Verdict 阶段去重规则

`crypto` 与 `secret` 两个 scanner 都会在源码中检测同一类模式（如 MD5 调用、AES 调用、加密库导入），verdict 阶段按以下规则去重：

- 同一 `file + line + check_item`（如 `foo.c:42:insecure_hash`）出现在两个 scanner 的 findings 中时，保留 severity 更高的一条；若 severity 相同，保留 `confidence` 更高的一条；若都相同则保留 `crypto` 的 finding。
- 同一 `file + line` 范围内（±5 行）出现多个相关 finding（如一个 MD5() 调用既被 `secret` 识别为弱哈希又被 `crypto` 识别为不安全算法），合并为一条 finding，evidence 拼接两者的证据。

### A3（Report 审计）

- 所有字段完整、数据一致、质量达标：PASS。
- 部分字段需补充：WARN，标记后输出。
- 缺失 finding 或 schema 校验失败：FAIL，重新生成。

### A3b（Redline 40 条覆盖矩阵审计）

- 综合报告必须根据 `references/redline-mapping.md` 输出 40 条覆盖矩阵：`clause_id`、`automation`、`profile_min`、`scanner_dims`、`finding_ids`、`manual_note`、`coverage_status`。
- automated/partial 项链接到实际 finding 或明确说明“未发现问题/无适用输入/降级未验证”。
- manual 项进入人工检查清单，不计入 automated FAIL 总数。
- 40 条缺任一条为 FAIL；automated/manual 重复计数为 FAIL。

## Agent 派发约束

- 每个 scanner session 只加载自己负责的 scanner 或 reporter 文件。
- scanner session 上下文只包含自身规则、分配文件列表、必要白名单、reference 数据、consumed finding 数据块和统一输出 schema。
- 单个分片不超过 50 个文件。
- 每个维度最多 8 个并发 agent，总 agent 上限 16。
- 每个 agent 最多重试 2 次，退避时间为 0s、5s、15s。

## 错误传播

```text
文件错误 -> Agent 错误 -> Phase 错误 -> 扫描错误
 (跳过)    (重试)       (降级)      (部分输出)
```

错误不跨级传播。文件错误不导致 Agent 失败，除非所有文件都失败。Agent 失败不导致 Phase 失败，除非超过当前 profile 维度数的 30%。

## Phase 级降级策略

| Phase | 降级行为 |
|-------|---------|
| Phase -1 | 终止扫描，输出错误报告和安装指南（degraded 状态仅当用户明确同意时设置） |
| Phase 0 | 终止扫描，输出错误报告和路径检查建议 |
| Phase 1 | 收集已完成结果，跳过失败维度，输出部分报告 |
| Phase 2 | 跳过验证，所有 findings 标记为 `unverified` |
| Phase 3 | 直接输出原始 JSON findings，跳过格式化报告 |

## 重试约束

```yaml
max_retries: 2
retry_backoff: [0s, 5s, 15s]
retry_timeout_multiplier: 1.5
phase_timeouts:
  preflight: 60s
  reconnaissance: 120s
  scan: 600s
  verdict: 300s
  report: 120s
cascade_failure_threshold: "profile_dimension_count * 0.30"
partial_degradation_threshold: 2
```

## Redline 扩展降级矩阵

| 工具/输入 | 不可用/异常 | 降级路径 | 最终状态 |
|----------|------------|---------|----------|
| OSV / grype / trivy | 不可达或缺失 | 使用 manifest/SBOM 静态证据与内置风险提示 | WARN + `audit_log` |
| ClamAV | 缺失 | `fileleak` 对病毒/木马项降级为人工项 | WARN |
| `communication_matrix_path` | 不存在或格式错误 | 仅输出 `port_inventory`，不硬判通信矩阵一致性 | WARN |
| semgrep / SAST 工具 | 缺失 | `secure-coding` 仅执行 grep/pattern 规则 | degraded |
| rpm / debsigs / cosign | 缺失 | `integrity` 标记 `needs_human` / `unverified` | WARN |
| redline mapping/spec 不一致 | 40 条覆盖校验失败 | 停止报告生成，要求重新导出/修正 mapping | FAIL |
| `context.consume()` 截断 | token_budget 不足 | 高 severity 优先并记录 A1b+ audit_log | WARN |

## 关键原则

1. 永不丢失已完成工作。
2. 部分结果优于无结果。
3. 透明失败，所有失败和降级都必须进入最终报告。
4. 所有报告、detail、suggestion、verdict_reasoning 使用简体中文。
