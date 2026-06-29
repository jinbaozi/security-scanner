# Orchestrator 编排指令

> 本文件定义 Orchestrator 的 Phase 调度逻辑、审计检查点和错误处理策略。

## 整体流程

```text
Phase -1: Pre-flight Check -> 审计 -> Phase 0: Recon -> 审计 A0
-> Phase 1: Parallel Scan -> 审计 A1 -> Phase 2: Verdict -> 审计 A2
-> Phase 3: Report -> 审计 A3 -> 输出
```

## Phase 调度规则

## 终端摘要格式

每个 Phase 完成后输出终端摘要，格式参见 `SKILL.md` 的执行流程示例。Phase 3 完成后输出完整扫描结果摘要，格式参见 `orchestration/reporter.md`。

### 顺序执行

Phase -1 和 Phase 0 必须顺序执行，前一 Phase 完成后才能进入下一 Phase。

### 并行执行

Phase 1 中 9 个维度扫描并行执行（6 老 + 3 新）。所有 Scanner 完成后设置 barrier，再进入 Phase 2。

### 条件跳过

- `elf_files` 为空：跳过 ELF Scanner。
- `source_shards` 为空：跳过 URL、Secret、Comment、Crypto、Network、Component-Info Scanner。
- `config_files` 为空：跳过 Secret、URL、Crypto、Network、Component-Info Scanner。
- `docker_files` 为空：Component-Info Scanner 的 root 启动信号降级为单源 INFERRED。
- `dependency_files` 为空：Crypto/Network Scanner 跳过库版本匹配，产出 `MISSING_LOCK_FILE` WARN finding。
- 对应依赖不可用且无降级方案（或用户已拒绝降级）：跳过该维度，记录 degraded_dimensions。

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

### A1（Scan 审计）

- 所有 Scanner 完成且输出符合 schema：PASS。
- 1 个 Scanner 失败：WARN，重试失败项（最多 2 次）。
- 2 个 Scanner 失败：WARN，标记失败维度但不影响主流程。
- 3-4 个 Scanner 失败：部分降级，继续其他维度。
- >= 5 个 Scanner 失败：FAIL，Phase 级降级。

### A2（Verdict 审计）

- 所有裁决包含 `confidence` 和 `verdict_reasoning`：PASS。
- 部分缺失：WARN，重新补充。
- 大面积缺失：FAIL，标记为 `unverified`。

### Verdict 阶段去重规则

`crypto-scanner` 与 `secret-scanner` 都会在源码中检测同一类模式（如 MD5 调用、AES 调用、加密库导入），verdict 阶段按以下规则去重：

- 同一 `file + line + check_item`（如 `foo.c:42:insecure_hash`）出现在两个 scanner 的 findings 中时，保留 severity 更高的一条；若 severity 相同，保留 `confidence` 更高的一条；若都相同则保留 crypto-scanner 的 finding。
- 同一 `file + line` 范围内（±5 行）出现多个相关 finding（如一个 MD5() 调用既被 secret-scanner 识别为弱哈希又被 crypto-scanner 识别为不安全算法），合并为一条 finding，evidence 拼接两者的证据。

### A3（Report 审计）

- 所有字段完整、数据一致、质量达标：PASS。
- 部分字段需补充：WARN，标记后输出。
- 缺失 finding 或 schema 校验失败：FAIL，重新生成。

## Agent 派发约束

- 每个 subagent 只加载自己负责的 scanner 或 reporter 文件。
- subagent 上下文只包含自身规则、分配文件列表、必要白名单和统一输出 schema。
- 单个分片不超过 50 个文件。
- 每个维度最多 8 个并发 agent，总 agent 上限 16。
- 每个 agent 最多重试 2 次，退避时间为 0s、5s、15s。

## 错误传播

```text
文件错误 -> Agent 错误 -> Phase 错误 -> 扫描错误
 (跳过)    (重试)       (降级)      (部分输出)
```

错误不跨级传播。文件错误不导致 Agent 失败，除非所有文件都失败。Agent 失败不导致 Phase 失败，除非达到级联阈值 4。

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
cascade_failure_threshold: 4
partial_degradation_threshold: 2
```

## 关键原则

1. 永不丢失已完成工作。
2. 部分结果优于无结果。
3. 透明失败，所有失败和降级都必须进入最终报告。
4. 所有报告、detail、suggestion、verdict_reasoning 使用简体中文。
