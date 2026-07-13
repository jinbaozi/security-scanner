# Pi Abort 恢复 SOP

## 原则

出现 abort、中断或 `risk=critical` 后，不要在同一高风险上下文中盲目重试。先保存或确认已有磁盘产物，再以紧凑上下文恢复；不得把内存状态视为唯一进度来源。

## Step 1：只检查 checkpoint 元数据

先用 `test -f`、`stat`、`wc -c` 检查，不读取正文：

1. `security-reports/pi-preflight.json`
2. `materialization-*.json`
3. `recon/scan-plan.summary.json`
4. `recon/shard-validation.json`
5. `audit/context-phase-*.json`
6. `elf-probe-*.json`
7. `findings/findings-*.json`
8. `findings-combined.json`
9. `*.audit.json`、`*.render.json` 和最终报告

不得读取完整路径列表、完整 Scan Plan、全量 findings 或完整报告正文来判断恢复点。

## Step 2：选择恢复点

| 已验证产物 | 恢复动作 |
|------------|----------|
| 仅 preflight | 从 Phase -0 开始 |
| materialization ready | 从 Phase 0 开始，不重复解包 |
| Scan Plan 摘要 + shard validation PASS | 从 Phase 1 开始 |
| 部分维度 findings | 仅重新调度缺失维度 |
| ELF checkpoint | 使用 `elf_hardening_probe.py --resume --checkpoint` |
| `findings-combined.json` | 从 Phase 3 开始 |
| render/audit 失败 | 仅重新渲染或拆分报告，不重跑扫描 |

每次恢复前运行 `scripts/pi_preflight.py` 和 `scripts/measure_context.py`。任何 checkpoint 必须先验证 JSON 可解析、状态字段合法、引用文件存在；损坏产物移入 `security-reports/recovery/quarantine/`，不得静默消费。

## Step 3：critical 处理

当 context audit 返回 `critical`：

1. 停止读取更多 artifact。
2. 写 `partial` 状态和当前 Phase/维度。
3. 将下一步改为 compact summary、batch 或新会话恢复。
4. 终端只输出状态、恢复点和报告目录。

若同一恢复点再次触发 critical，不继续自动重试；要求缩小目标、拆分扫描或调整经过确认的运行时配置。

## Phase 3 恢复

- required placeholder 缺失：修正 values 后 strict 重渲，最多 2 次。
- `output_too_large`：生成紧凑索引，将正文拆入维度报告或 `details/`。
- residual 超过门限且审计为 `critical`：停止重渲循环，保留 audit JSON，检查模板与 values 命名契约。
- 已通过 A4 的文件不得重复生成，除非上游 finding checkpoint 发生变化。
