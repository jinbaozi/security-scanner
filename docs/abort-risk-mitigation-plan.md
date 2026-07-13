# Pi Agent "Unhandled stop reason: abort" 风险分析与修复方案

> 文档目的：梳理 security-scanner skill 在 Pi Agent 中执行时可能触发 `abort` 的所有风险点，给出可落地的修复方案，供后续评审与实施。
>
> 文档状态：v1 已实施（P0-1 至 P0-5、P1-6 至 P1-9、P2-10/P2-11 已落地并具备自动化测试）。
>
> 关联分支：`feat/safe-render-template`（已落地 Step 1-5/10 的 `[[UPPER_SNAKE]]` 安全渲染修复）。

---

## 1. abort 错误语义还原

`Unhandled stop reason: abort` 是 Pi Agent runtime 抛出的**未捕获停止信号**，常见触发源：

| 来源 | 含义 | 触发后行为 |
|------|------|-----------|
| 上下文窗口溢出 | 输入 token 超过模型上限 | runtime 主动 abort 当次响应 |
| 单次工具输出超限 | `bash`/`read` 返回内容超过单次限额 | runtime 截断并 abort |
| 输出 token 超限 | 模型本轮输出超过 max_tokens | runtime abort 生成过程 |
| 工具超时 | `bash` 命令运行超过 timeout | runtime abort 工具调用 |
| 内部 panic | runtime 自身 bug / OOM | 异常路径，无 fallback |

**关键性质**：

- abort 发生在 runtime 层，**不进 stdout/stderr**。
- 用户终端只看到 `Unhandled stop reason: abort` 一行。
- skill 代码**无法捕获也无法 retry**。
- 当前 turn 立即终止，下次 session 必须从头开始（in-memory state 不保留）。

因此**所有保护必须预防性执行，不能依赖 try/except**。

---

## 2. 实测瓶颈估算

| 资源 | 估算上限 | 安全阈值 | 实测突破点 |
|------|---------|---------|-----------|
| 单次工具输出 | ~32 KB | < 16 KB | `scan_plan.json` 13 MB |
| 单次 `read` 返回 | ~64 KB | < 32 KB | 240 KB JSON read |
| 单回合累计输入 | ~100K tokens | < 50K tokens | 多次 grep + read 累计 |
| 单回合输出 | ~16K tokens | < 8K tokens | 38 KB 综合报告 |
| bash timeout | 600s | < 120s | `rpmbuild -bp` 287s |
| tool call stack | ~10 层 | < 5 层 | 嵌套 subagent |

---

## 3. 各阶段风险点清单

| ID | 阶段 | 风险 | 严重度 | 状态 |
|----|------|------|-------|------|
| P0-1 | Phase 0 | `scan_plan.json` 13 MB | 高 | 已修复：紧凑 schema + 64 KiB 摘要 |
| P0-2 | Phase -0 | materializer 无子进程超时 | 高 | 已修复：分命令 timeout + command_log |
| P0-3 | Phase 1.5 | 大 grep 输出未截断（实测 19,136 行） | 高 | 已修复：safe_grep 有界 JSON |
| P0-4 | Phase 0 | shard 50 文件硬限制被违反（实测 200） | 中 | 已修复：validate_shards 门禁 |
| P0-5 | 全局 | 无 context 自检工具 | 根本 | 已修复：Phase 边界 measure_context 门禁 |
| P1-6 | Phase 3 | render 输出无大小限制 | 中 | 已修复：64 KiB 门禁 + 分章节降级 |
| P1-7 | Phase 3 | audit_render.py 无 critical 级别 | 中 | 已修复：残留门限 + 退出码 6 |
| P1-8 | Phase 1 | elf probe 无 batch/resume | 中 | 已修复：batch/checkpoint/resume |
| P1-9 | 全局 | 无 Pi Agent runtime 限制文档 | 低 | 已修复：项目阈值文档 |
| P2-10 | 全局 | 无 abort 应急 SOP | 可后置 | 已修复：checkpoint 恢复 SOP |
| P2-11 | Phase 1.5 | scanner 输出无截断指引 | 可后置 | 已修复：200 finding 上限 + evidence 聚合 |

**已修复（跳过）**：

- f-string `{var}` NameError 崩溃 → Step 1-5 `[[UPPER_SNAKE]]` 安全渲染
- 模板 `{}` 与 f-string 语法冲突 → Step 4-5 重写所有模板
- `audit_render.py` 直接运行找不到模块 → Step 10 sys.path bootstrap

---

## 4. 详细修复方案

### P0-1：scan_plan.json 13 MB 单文件输出

**问题**：实测生成的 `scan_plan.json` 达 **13,198,049 字节**。根因是 `all_files` / `source_shards` 字段把 27,962 个绝对路径全部序列化进 JSON。Pi Agent 单次 `read` 立刻 abort。

**修复方案**：

1. **新增 `scripts/summarize_scan_plan.py`**：
   - CLI：`python3 scripts/summarize_scan_plan.py --input scan_plan.json --output scan_plan.summary.json --sample-size 50`
   - 输出 schema：

     ```json
     {
       "version": "1.0",
       "component_name": "binutils",
       "total_files": 27962,
       "scan_files": 27476,
       "elf_count": 27,
       "source_count": 2243,
       "excluded_count": 486,
       "source_shards_count": 20,
       "shard_size_distribution": {"min": 4, "max": 200, "median": 90, "p95": 200},
       "samples": {
         "elf": ["...addr2line", "...ar", "...as"],
         "source": ["...bfd/bfd.c"],
         "excluded": ["...zlib/..."]
       },
       "warnings": ["shard size 200 exceeds spec limit of 50 (degraded)"],
       "truncated": true
     }
     ```

   - **关键约束**：输出 < 64 KB；`path` 截断为 basename + 顶层目录；samples 数组上限 50。

2. **修改 `scripts/package_materializer.py`**：
   - `_record_build_roots` 输出 `path` + `file_count`，不展开全量文件。

3. **修改 `orchestration/reconnaissance.md`**：
   - 新增 "Scan Plan 产物大小约束" 段：
     - `scan_plan.json` 严禁超过 1 MB
     - `all_files` / `source_shards[*].files` 只保留计数 + sample
     - 摘要版写到 `scan_plan.summary.json`（< 64 KB）
     - 全量路径只在分片执行期间存在

**验证**：
- binutils 上 `scan_plan.json` 13 MB → `scan_plan.summary.json` < 64 KB。
- `read scan_plan.summary.json` 不触发 abort。

**涉及文件**：

| 文件 | 操作 |
|------|------|
| `scripts/summarize_scan_plan.py` | 新建 |
| `scripts/package_materializer.py` | 修改 `_record_build_roots` |
| `orchestration/reconnaissance.md` | 追加产物大小约束段 |
| `orchestration/orchestrator.md` | 引用 summarize 步骤 |

**工作量**：0.5 人日。

---

### P0-2：materializer 无子进程超时

**问题**：`scripts/package_materializer.py` 中所有 `subprocess.run` 调用无 `timeout` 参数。`rpmbuild -bp --nodeps` 在 binutils 上跑 5-8 分钟，如果 Pi Agent 默认 timeout 较短会被 abort，且 SRPM 已解包但 BUILD 半成品。

**修复方案**：

1. **新增 `scripts/_subprocess_utils.py`**：

   ```python
   DEFAULT_TIMEOUTS = {
       "rpm2cpio": 120,
       "cpio": 300,
       "rpmbuild": 1800,
       "dnf": 600,
       "tar": 300,
       "patch": 60,
   }

   class CommandResult:
       ok: bool
       returncode: int
       stdout: str
       stderr: str
       timed_out: bool
       duration_seconds: float

   def run_with_timeout(cmd, *, timeout, **kwargs) -> CommandResult: ...
   ```

2. **修改 `scripts/package_materializer.py`**：
   - 统一封装 `subprocess.run`，强制 `timeout=`。
   - `rpm2cpio`/`cpio` 超时 → `status=blocked`。
   - `rpmbuild -bp` 超时 → `status=degraded` + 保留已发现 `source_roots`。

3. **materialization.json 增加 `duration_seconds`**：
   - 每次子进程完成记录 `started_at`/`finished_at`，写入 `audit_log`。

**验证**：
- 构造 patch 冲突 mock spec，触发 rpmbuild 长时间运行。
- 设 timeout=10s，脚本返回 `status=degraded` 而非 runtime abort。
- 真实 binutils 扫描 `rpmbuild -bp` 287.5s < 1800s，正常完成。

**涉及文件**：

| 文件 | 操作 |
|------|------|
| `scripts/_subprocess_utils.py` | 新建 |
| `scripts/package_materializer.py` | 重构 subprocess 调用 |
| `orchestration/orchestrator.md` | Phase -0 异常段引用 |

**工作量**：0.5 人日。

---

### P0-3：大 grep 输出未截断

**问题**：实测 grep 输出未截断：

```
crypto 关键词 grep → 4,102 行
MD5/SHA1/SHA256 grep → 19,136 行
```

agent 直接执行会把 19k 行返回到上下文，单次吃光所有 token。

**修复方案**：

1. **新增 `scripts/safe_grep.py`**：

   ```bash
   python3 scripts/safe_grep.py \
       --pattern "MD5|SHA1" \
       --root /path/to/src \
       --include "*.c,*.h" \
       --max-count 200 \
       --max-bytes 32768 \
       --output safe-grep-result.txt
   ```

   **关键参数**：

   | 参数 | 默认 | 作用 |
   |------|------|------|
   | `--max-count` | 200 | 命中行数上限 |
   | `--max-bytes` | 32 KB | 输出字节上限 |
   | `--per-file-cap` | 20 | 单文件命中上限 |

   **输出 schema**：

   ```json
   {
     "pattern": "MD5|SHA1",
     "matched_files": 89,
     "matched_lines": 19136,
     "truncated": true,
     "truncation_reason": "max_count=200 reached",
     "samples": [{"file": "...", "line": 2630, "match": "case DW_LNCT_MD5:"}],
     "summary": {
       "top_dirs": {"bfd": 45},
       "extensions": {".c": 178}
     }
   }
   ```

2. **修改 `scanners/*/scanner.md` 共 13 份**：
   - 每个 scanner 的 Step 2（grep 阶段）必须使用 `safe_grep.py`，禁止裸 `grep -rE`。
   - 模板：

     ```markdown
     ## Step 2: 模式搜索

     **必须使用** `scripts/safe_grep.py`，禁止直接调用 `grep -rE`。

     ```bash
     python3 scripts/safe_grep.py \
         --pattern 'MD5|SHA1' \
         --root "$SRC" \
         --include "*.c,*.h" \
         --max-count 500 \
         --output reports/crypto-grep.json
     ```

     如果返回 `truncated=true`，scanner 必须读取 `summary.top_dirs` 字段作为代表性输入。
     ```

**验证**：
- binutils 上 `safe_grep.py --pattern 'MD5|SHA1'` 输出 < 32 KB。
- `truncated=true`，`summary.top_dirs` 完整。

**涉及文件**：

| 文件 | 操作 |
|------|------|
| `scripts/safe_grep.py` | 新建 |
| `scanners/crypto/scanner.md` 等 13 份 | grep 段改写 |

**工作量**：1 人日。

---

### P0-4：shard 50 文件硬限制被违反

**问题**：`orchestration/reconnaissance.md` 规定分片 ≤ 50 文件，实测生成 200 文件 shard：

```
shard 0: src/bfd (200 files)
shard 1: src/bfd (200 files)
```

agent 在 recon 阶段违反 spec，且 orchestrator 无校验。单 shard 200 文件 → 长时间运行 + finding 输出可能 50+ KB → 注入 context 触发 abort。

**修复方案**：

1. **修改 `orchestration/reconnaissance.md`**：明确 shard 违规处理：
   - 单个 shard 文件数 ≤ **50**（绝对上限）。
   - 超出 50 时禁止 silently 合并，必须拆分或标记 degraded。
   - 任何 shard > 100 文件触发 P0 FAIL，A0 审计必须拒绝。

2. **新增 `scripts/validate_shards.py`**：

   ```python
   MAX_SHARD_FILES = 50
   WARN_SHARD_FILES = 40
   MAX_SHARDS_PER_DIM = 8
   MAX_TOTAL_SHARDS = 16

   def validate(shards) -> ValidationResult: ...
   ```

   退出码：0=pass, 2=warnings, 3=errors。

3. **修改 recon agent 行为约束**：
   - shards 输出后**必须**调用 `scripts/validate_shards.py`。
   - errors 非空 → A0 FAIL，重新分片。
   - warnings 非空 → A0 WARN，继续但 audit_log 记录。

**验证**：
- 故意构造 200 文件 shard，validate_shards 应报错。
- binutils 当前 20 shard ≤ 50 文件，pass。

**涉及文件**：

| 文件 | 操作 |
|------|------|
| `scripts/validate_shards.py` | 新建 |
| `orchestration/reconnaissance.md` | shard 约束段重写 |
| `orchestration/orchestrator.md` | A0 审计段引用 |

**工作量**：0.3 人日。

---

### P0-5：无 context 自检工具

**问题**：agent 在每个阶段**没有任何 token 估算**，只能在 abort 后才发现超限。缺少预防性自检。

**修复方案**：

1. **新增 `scripts/measure_context.py`**：

   ```bash
   python3 scripts/measure_context.py \
       --phase phase-0 \
       --inputs materialization.json recon/shards.json recon/all_files.txt
   ```

   **输出 schema**：

   ```json
   {
     "phase": "phase-0",
     "estimated_tokens": {
       "input_so_far": 12450,
       "tool_outputs_total": 89432,
       "next_step_budget": 32118
     },
     "risk_level": "medium",
     "warnings": ["tool_outputs_total 89KB > 64KB safe threshold"],
     "recommendations": [
       "summarize recon/all_files.txt to < 64KB before read",
       "use safe_grep.py for any further searches"
     ]
   }
   ```

   **估算方法**：
   - 文本文件：`bytes / 3`。
   - JSON 文件：`len(json.dumps(content)) / 3`。
   - grep 输出：行数 × 50 token。
   - finding JSON：finding 数 × 200 token。

   **风险阈值**：

   | 累计输入 token | 风险 |
   |----------------|------|
   | < 30K | low |
   | 30K-60K | medium |
   | 60K-100K | high |
   | > 100K | critical（立即自检） |

2. **Orchestrator 集成**：
   - 在 Phase 0/1/2/3 切换点增加自检。
   - `risk_level=high/critical` → 触发 summary 步骤。
   - `risk_level=critical` → 强制停止，等待人工确认。

**验证**：
- binutils Phase 0 完成后跑 `measure_context.py`，返回准确估算。
- 故意构造 500 KB 工具输出，验证 `risk_level=high`。

**涉及文件**：

| 文件 | 操作 |
|------|------|
| `scripts/measure_context.py` | 新建 |
| `orchestration/orchestrator.md` | 阶段切换自检段 |
| `references/render-audit.md` | 引用自检步骤 |

**工作量**：0.5 人日。

---

### P1-6：render 输出大小限制

**问题**：当前 `render_template.py` 渲染 binutils 综合报告输出 38 KB。finding 数翻倍可能突破 100 KB，对下游 `read` 造成压力。

**修复方案**：

1. **修改 `scripts/render_template.py`**：
   - 新增 `--max-output-size` 参数（默认 65536 bytes）。
   - 超限时抛 `ValueError`，退出码 4。

2. **触发降级**：
   - 渲染拒绝写入文件。
   - Reporter 写 `degradation_reason="output_too_large"`。
   - 改写为"分章节报告 + 索引"。

3. **Reporter 配合**：
   - 输出超限处理：拆 `summary.md`（< 32 KB）+ `details/` 目录（13 个独立文件）。

**验证**：
- binutils 综合报告 38 KB < 64 KB 默认上限，pass。
- 故意构造 100 KB 模板，触发 ValueError。

**涉及文件**：

| 文件 | 操作 |
|------|------|
| `scripts/render_template.py` | 新增参数与检查 |
| `orchestration/reporter.md` | 输出超限处理段 |

**工作量**：0.2 人日。

---

### P1-7：audit_render.py residual 警告升级

**问题**：当前 `audit_render.py` 对残留 placeholder 仅返回 warn/fail，**没有 critical 级别**。如果 residual 数量飙升（50+），意味着渲染大面积失败，agent 应立即停止。

**修复方案**：

1. **修改 `scripts/audit_render.py`**：
   - 新增 `--max-residual` 参数（默认 20）。
   - 超限返回 `status=critical, abort_risk=true`，退出码 6。

2. **Reporter 集成**：
   - 退出码 6 → 立即停止 Phase 3。
   - 写 `audit_log.abort_reason="excessive_residual_placeholders"`。
   - 强制降级：只输出 summary + index，不输出详细 finding 表格。

**验证**：
- 构造 30 个 residual 的场景，audit 返回 critical。
- Reporter 接收到 critical 后停止输出。

**涉及文件**：

| 文件 | 操作 |
|------|------|
| `scripts/audit_render.py` | 新增参数与 critical 状态 |
| `orchestration/reporter.md` | critical 处理段 |

**工作量**：0.2 人日。

---

### P1-8：elf probe 批处理与 resume

**问题**：`elf_hardening_probe.py` 当前 `--list-file` 一次性跑所有 ELF。如果 ELF 数 > 100，单次跑 60+ 秒，且无 resume 机制。Agent 中途 abort 后下次必须从头跑。

**修复方案**：

1. **修改 `scripts/elf_hardening_probe.py`**：
   - 新增 `--batch-size`（默认 20）。
   - 新增 `--resume`：跳过 `--output-json` 中已存在的文件。
   - 新增 `--checkpoint`：每个 batch 后立即保存。

2. **Orchestrator 集成**：

   ```bash
   python3 scripts/elf_hardening_probe.py \
       --list-file $ELF_LIST \
       --output-json $PROBE_JSON \
       --batch-size 20 \
       --checkpoint \
       --resume
   ```

   - 每次 batch 后立即 checkpoint。
   - 运行时 abort 后下次 `--resume` 接续。

**验证**：
- 模拟 abort：跑 50 个 ELF 时 kill 进程，resume 只跑剩余。
- binutils 27 个 ELF 单 batch 内完成。

**涉及文件**：

| 文件 | 操作 |
|------|------|
| `scripts/elf_hardening_probe.py` | 新增参数 |
| `orchestration/orchestrator.md` | ELF 探测段 |

**工作量**：0.3 人日。

---

### P1-9：新增 `references/agent-runtime-limits.md`

**问题**：当前 skill 没有文档记录 Pi Agent 的硬约束，导致每个 agent session 都可能因不熟悉限制而触发 abort。

**修复方案**：

1. **新增 `references/agent-runtime-limits.md`**：

   ```markdown
   # Pi Agent Runtime 硬约束（实测值）

   ## 输入侧

   | 资源 | 实测上限 | 安全阈值 | 触发 abort 条件 |
   |------|---------|---------|----------------|
   | 单次 tool output (bash) | ~32 KB | < 16 KB | > 32 KB 立即截断 |
   | 单次 `read` 返回 | ~64 KB | < 32 KB | > 64 KB 触发 abort |
   | 单回合累计 input | ~100K token | < 50K | > 80K 高风险 |
   | 单回合 output | ~16K token | < 8K | > 12K 截断 |

   ## 工具调用

   | 资源 | 实测上限 |
   |------|---------|
   | bash timeout 默认 | 600s |
   | tool call stack | ~10 层 |
   | 并发 tool calls | 单 agent 串行 |

   ## 与 abort 的关系

   abort 不是可捕获的 Python 异常，是 runtime 主动中断：

   - 不进入 stdout/stderr
   - 当前 turn 立即终止
   - 下次 session 从头开始

   因此**所有保护必须预防性执行，不能依赖 try/except 捕获**。
   ```

2. **SKILL.md / orchestration/orchestrator.md 引用该文档**。

**验证**：
- 文档存在并被引用。

**涉及文件**：

| 文件 | 操作 |
|------|------|
| `references/agent-runtime-limits.md` | 新建 |
| `SKILL.md` | 引用段 |
| `orchestration/orchestrator.md` | 引用段 |

**工作量**：0.2 人日。

---

### P2-10：abort 应急 SOP（可后置）

**修复方案**：

1. **新增 `references/abort-recovery.md`**：

   ```markdown
   # Abort 应急恢复 SOP

   ## 检测 abort

   用户终端出现 `Unhandled stop reason: abort` 时：

   1. **不要尝试 retry 当前 turn**（同一上下文立即再次 abort）
   2. **开启新 session**，从 Phase 0 重新开始
   3. **优先 read checkpoints**：
      - `security-reports/materialization.json`
      - `security-reports/recon/shards.json`
      - `security-reports/elf-probes/elf-probe-*.json`
      - `security-reports/findings/findings-*.json`

   ## 恢复策略

   | 已完成 Phase | 恢复策略 |
   |--------------|---------|
   | Phase -0 | 直接进入 Phase 0 |
   | Phase 0 | 直接进入 Phase 1 |
   | Phase 1 ELF | `elf_hardening_probe.py --resume` |
   | Phase 1 其它 | 重新调度该维度 scanner |
   | Phase 2 | 从 `findings-combined.json` 读 finding，进入 Phase 3 |
   | Phase 3 | 重新执行 render + audit |

   ## 一票否决

   如果 `risk_level=critical`，**强制中断**：

   - 输出 partial 报告
   - 写 `audit_log.abort_reason="context_critical"`
   - 要求人工拆分任务或扩大 context 上限
   ```

**工作量**：0.2 人日。

---

### P2-11：scanner 输出截断指引（可后置）

**修复方案**：

1. **新增 `references/scanner-output-limits.md`**：

   | 维度 | finding 上限 | 超限策略 |
   |------|-------------|----------|
   | elf | 200 | 按文件聚合 |
   | url | 100 | 按 host 聚合 |
   | secret | 50 | 仅报告 unique 凭证 |
   | comment | 50 | 取 TOP-N 文件 |

2. **修改各 scanner.md**：
   - Step 5b 输出截断：finding > 200 时按 severity 排序取前 100 + 后 100，写 `audit_log.truncated_count`。

**工作量**：0.5 人日。

---

## 5. 实施优先级与工作量

| 优先级 | 风险点 | 工作量（人日） | 累计 |
|--------|-------|--------------|------|
| **P0** | P0-1 scan_plan 截断 | 0.5 | 0.5 |
| **P0** | P0-2 materializer timeout | 0.5 | 1.0 |
| **P0** | P0-3 safe_grep | 1.0 | 2.0 |
| **P0** | P0-4 shard 校验 | 0.3 | 2.3 |
| **P0** | P0-5 context 自检 | 0.5 | 2.8 |
| P1 | P1-6 render size limit | 0.2 | 3.0 |
| P1 | P1-7 audit critical | 0.2 | 3.2 |
| P1 | P1-8 elf probe 批处理 | 0.3 | 3.5 |
| P1 | P1-9 runtime limits 文档 | 0.2 | 3.7 |
| P2 | P2-10 abort SOP | 0.2 | 3.9 |
| P2 | P2-11 scanner 截断 | 0.5 | 4.4 |

**总工作量：约 4.4 人日**

---

## 6. 推荐实施顺序

按"防 abort 价值 / 实施成本"比：

```
1. P0-3 safe_grep.py          （消灭最大 abort 源：19k 行 grep）
2. P0-5 measure_context.py    （预防性自检，零侵入）
3. P0-1 scan_plan 摘要化       （消除已知 13 MB 隐患）
4. P0-4 shard 校验            （防止 spec 违规累积）
5. P0-2 materializer timeout  （防止 rpmbuild 卡死）
6. P1-6/7/8/9                （提升稳定性）
7. P2-10/11                  （长期维护性）
```

---

## 7. 评审 Checklist

评审本方案时建议核对：

- [ ] 11 项风险点是否完整覆盖
- [ ] 每项修复方案的"涉及文件"是否完整
- [ ] 工作量估算是否合理（团队 velocity 校准）
- [ ] P0/P1/P2 优先级是否符合实际业务诉求
- [ ] 实施顺序是否符合依赖关系
- [ ] 是否需要拆分到多个 PR / 多个 sprint
- [ ] 是否需要补充单元测试 / 集成测试方案
- [ ] 是否需要回滚预案

---

## 8. 关联材料

- 当前分支：`feat/safe-render-template`
- 已落地 commit：
  - `56ef264` feat(render): add safe renderer, audit, contract templates (steps 1-5)
  - `59b8dd7` feat(render): wire safe renderer into SKILL/orchestrator docs (steps 6-9)
  - `ca032b2` fix(audit): allow scripts/audit_render.py to run as standalone CLI
- 关联文档：
  - `references/render-audit.md`（已落地）
  - `templates/report-comprehensive.md`（已重写）
  - `templates/report-*.md` 13 份（已重写）
- 关联脚本：
  - `scripts/render_template.py`（已落地）
  - `scripts/audit_render.py`（已落地）

---

**文档版本**：v1.0
**最后更新**：2026-07-10
**作者**：Pi Agent（security-scanner skill）
**状态**：v1 风险项已全部完成