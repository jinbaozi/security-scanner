# Security Scanner 紧凑运行路由

> Pi 激活时只加载本文件。完整 `orchestration/orchestrator.md` 是详细规范源，不得在激活时整文件读取；仅在对应 Phase 出现歧义时，先用 `rg -n '^###? '` 定位标题，再通过 `read(offset, limit)` 读取所需小节。

## 初始化

1. `SKILL_ROOT`：已加载 `SKILL.md` 的父目录绝对路径。
2. `TARGET_ROOT`：用户目标绝对路径。
3. `REPORT_ROOT`：目录目标使用 `$TARGET_ROOT/security-reports`；包文件使用其父目录下的 `security-reports`。
4. 执行 `$SKILL_ROOT/scripts/pi_preflight.py`，详细结果写 `$REPORT_ROOT/pi-preflight.json`。
5. 默认 `scan_profile=redline-full`；非法 profile 立即停止。

终端每个 Phase 最多一行，最终最多八行。完整 JSON、文件清单、findings、报告正文及工具 stdout/stderr 只写入 `REPORT_ROOT`，不得回显或整文件读取。

## SKILL 只读执行边界

扫描期间，`SKILL_ROOT 及其所有子路径均为只读输入`。任何 LLM、subagent 或运行期工具都不得修改、创建、删除、重命名其中的文件，不得修改权限或运行 Git/补丁/格式化/代码生成命令。所有输出必须写入外部 `REPORT_ROOT`；`REPORT_ROOT` 的真实路径等于或位于 `SKILL_ROOT` 内时必须立即 `BLOCKED`，不得以临时文件、软链接或 `../` 绕过。发现 skill 缺陷只记录外部审计产物，不得修改本 SKILL。生产环境必须同时使用只读挂载或 harness 写入拒绝策略。

Phase -1 使用 `verify_skill_integrity.py snapshot --skill-root "$SKILL_ROOT" --output "$REPORT_ROOT/skill-integrity-baseline.json"` 建立外部基线；每个 Phase 边界使用 `verify_skill_integrity.py verify --skill-root "$SKILL_ROOT" --baseline "$REPORT_ROOT/skill-integrity-baseline.json" --output "$REPORT_ROOT/skill-integrity-<phase>.json"` 校验。返回 6 时立即停止，且不得自动恢复或覆盖变化文件。完整性快照是检测门禁，不能替代文件系统只读保护。

## 按 Phase 加载

| Phase | 仅按需加载 | 主要 checkpoint |
|------|------------|-----------------|
| -1 依赖预检 | `references/dependency-check.md` | `pi-preflight.json`、依赖状态 |
| -0 输入物化 | 标准调用：`package_materializer.py --target "$TARGET_ROOT" --report-dir "$REPORT_ROOT" --output-json "$REPORT_ROOT/materialization.json"`；异常时读 orchestrator 的“Phase -0”小节 | `materialization.json` |
| 0 Recon | `orchestration/reconnaissance.md`；`normalize_shards.py`、`validate_shards.py`、`summarize_scan_plan.py` | `scan-plan.summary.json`、shard validation、路径 list 文件 |
| 1/1.5 扫描 | 调用 `resolve_scanners.py`；仅加载当前维 `meta.yaml`、`scanner.md` 和 scope 非 `tool` 的声明 references | `scanner-registry-plan.json`、`findings/findings-<dim>.json` |
| 2 裁决 | `references/verdict-rules.md`、`references/finding-schema.md` | `findings-combined.json` |
| 3 报告 | `orchestration/reporter.md`、manifest、当前模板；A3b 才读 redline spec/mapping | 综合 JSON/Markdown、13 维报告 |

每个 Phase 只加载表中内容。禁止预读全部 scanner、template、findings、`redline-spec.md` 或完整 orchestrator。

## Phase 状态机

```text
-1 preflight -> -0 materialize -> 0 recon -> 1 scan -> 2 verdict -> 3 report
```

每个 Phase 执行 `PASS/WARN/FAIL` 审计：PASS 继续；WARN 写审计后继续；FAIL 最多修复两次，仍失败则保存已有 checkpoint 并按详细规范降级。需要具体门禁时只读取 `orchestration/orchestrator.md` 中对应 `A-0`、`A0`、`A1`、`A2`、`A3/A4` 小节。

## Scanner 执行模式

- harness 有 subagent/session 工具：按 registry 拓扑使用独立 session。
- Pi 无该工具：当前 session 串行形成逻辑 session，一次只加载一个维度；结果落盘后再处理下一维。
- 禁止递归启动 `pi`，禁止把其他维 scanner prompt 注入当前维。
- 上游 finding 只通过 `ScanContext.consume(..., compact=True)` 注入；原始 finding 保留在磁盘和 ScanContext。
- 单维 finding 上限 200；超限规则按需读取 `references/scanner-output-limits.md`，聚合审计必须记录 `truncated_count` 和 evidence 引用。
- 禁止对 `$SKILL_ROOT/scanners/registry` 目录调用 `read` 或 `cat *`；必须调用 `resolve_scanners.py --skill-root "$SKILL_ROOT" --profile "$SCAN_PROFILE" --output "$REPORT_ROOT/scanner-registry-plan.json"`。
- 模式搜索必须使用 `$SKILL_ROOT/scripts/safe_grep.py`；`--files-file` 必须取自 Scan Plan `file_lists.<class>.path` 或 `source_shards[*].file_list`，并相对 `$REPORT_ROOT` 解析，`--base-root` 必须取自 materialization 的对应 source/binary root。禁止猜测 `manifest-files.txt` 等文件名，禁止把 `--base-root` 当成清单生成器，禁止在清单缺失时静默改为递归扫描。
- 内容合规维度只能调用 `content_compliance_probe.py` 加载本地规则；禁止在 prompt、shell 参数或模型输出中拼接规则原文，禁止读取 raw evidence 正文。

## 恢复与上下文保护

详细阈值与恢复流程按需读取 `references/agent-runtime-limits.md` 和 `references/abort-recovery.md`，不得在正常激活时预读。

- 每个 Phase 边界调用 `$SKILL_ROOT/scripts/measure_context.py`，仅按 artifact 大小估算；`medium/high` 切换 compact/batch，`risk=critical` 停止模型注入并写 partial checkpoint。
- 每个 Phase 和维度完成后立即落盘 checkpoint，不依赖对话内存保存唯一状态。
- 读取 JSON/报告前先检查字节数；优先读取紧凑摘要，必要时使用 `offset/limit` 分段。
- 不把完整路径数组写入 Scan Plan 或模型上下文；路径只写 list 文件，Pi 只读不超过 64 KiB 的摘要。
- 文件分片每组绝对上限 50 个；先调用 `normalize_shards.py` 确定性拆分超限 shard，再调用 `validate_shards.py`。超过 16 片依据 `execution_batches` 分批串行，不得增大单片上限。
- 调用 `references/tool-cli-contracts.json` 登记的运行期 CLI 前必须读取对应机器契约并按 argv 数组（`shell=False` 语义）执行；code 2 只归类为 `cli_contract_error`，3=warn/degraded、4=failed、5=blocked、6=critical，禁止猜参数重试。文件清单必须先经 `resolve_artifact.py` 解析。
- 工具失败只在终端输出一行分类，命令、argv、退出码和截断 stderr 写审计 JSON。
- 禁止用 shell heredoc 临时编写 findings 转换、grep evidence 读取或“补齐维度”Python；safe-grep 样本复核必须先调用 `summarize_grep_evidence.py`，消费 `samples[].match` 的版本化 schema。必须使用版本化脚本并先通过 `py_compile`/测试。维度没有可信结果时写 `blocked/degraded/skipped/unverified` 覆盖状态，不得补默认 PASS。
- Phase 3 调用 `report_pipeline.py`，由其按 manifest 对综合报告和 13 个维度报告执行 `build_report_values.py`、`render_template.py` 和 `audit_render.py`；strict 缺必填字段返回 4，不得原样重试或打印 traceback。
