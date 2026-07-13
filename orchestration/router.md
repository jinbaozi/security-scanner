# Security Scanner 紧凑运行路由

> Pi 激活时只加载本文件。完整 `orchestration/orchestrator.md` 是详细规范源，不得在激活时整文件读取；仅在对应 Phase 出现歧义时，先用 `rg -n '^###? '` 定位标题，再通过 `read(offset, limit)` 读取所需小节。

## 初始化

1. `SKILL_ROOT`：已加载 `SKILL.md` 的父目录绝对路径。
2. `TARGET_ROOT`：用户目标绝对路径。
3. `REPORT_ROOT`：目录目标使用 `$TARGET_ROOT/security-reports`；包文件使用其父目录下的 `security-reports`。
4. 执行 `$SKILL_ROOT/scripts/pi_preflight.py`，详细结果写 `$REPORT_ROOT/pi-preflight.json`。
5. 默认 `scan_profile=redline-full`；非法 profile 立即停止。

终端每个 Phase 最多一行，最终最多八行。完整 JSON、文件清单、findings、报告正文及工具 stdout/stderr 只写入 `REPORT_ROOT`，不得回显或整文件读取。

## 按 Phase 加载

| Phase | 仅按需加载 | 主要 checkpoint |
|------|------------|-----------------|
| -1 依赖预检 | `references/dependency-check.md` | `pi-preflight.json`、依赖状态 |
| -0 输入物化 | `scripts/package_materializer.py --help`；异常时读 orchestrator 的“Phase -0”小节 | `materialization-*.json` |
| 0 Recon | `orchestration/reconnaissance.md`；`validate_shards.py`、`summarize_scan_plan.py` | `scan-plan.summary.json`、shard validation、路径 list 文件 |
| 1/1.5 扫描 | registry API；当前维 `meta.yaml`、`scanner.md` 和声明 references | `findings/findings-<dim>.json` |
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
- 模式搜索必须使用 `$SKILL_ROOT/scripts/safe_grep.py`；禁止执行会向终端返回全部命中的递归 grep。

## 恢复与上下文保护

详细阈值与恢复流程按需读取 `references/agent-runtime-limits.md` 和 `references/abort-recovery.md`，不得在正常激活时预读。

- 每个 Phase 边界调用 `$SKILL_ROOT/scripts/measure_context.py`，仅按 artifact 大小估算；`medium/high` 切换 compact/batch，`risk=critical` 停止模型注入并写 partial checkpoint。
- 每个 Phase 和维度完成后立即落盘 checkpoint，不依赖对话内存保存唯一状态。
- 读取 JSON/报告前先检查字节数；优先读取紧凑摘要，必要时使用 `offset/limit` 分段。
- 不把完整路径数组写入 Scan Plan 或模型上下文；路径只写 list 文件，Pi 只读不超过 64 KiB 的摘要。
- 文件分片每组绝对上限 50 个；超过 16 片时分批串行，不得增大单片上限。
- 工具失败只在终端输出一行分类，命令、退出码和截断 stderr 写审计 JSON。
- Phase 3 使用 `$SKILL_ROOT/scripts/render_template.py` 和 `audit_render.py`；strict 缺必填字段返回 4，不打印 traceback。
