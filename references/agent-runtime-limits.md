# Pi Agent 运行时与上下文安全策略

> 本文记录 security-scanner 的**项目安全阈值**，不是 Pi 官方固定上限。不同模型、provider、Pi 版本和 harness 工具配置可能不同；阈值只能更严格，不能据此推断运行时一定允许更大输入。

## 项目安全阈值

| 资源 | 默认策略 | 超限处理 |
|------|----------|----------|
| 单次终端输出 | 不超过 16 KiB；脚本通常只输出 1 行 | 正文写 JSON/日志，只返回计数和路径 |
| 单次 Read | 优先不超过 32 KiB | 先看大小和紧凑摘要，再使用 offset/limit |
| 模型可读摘要 | 硬上限 64 KiB | 超过 32 KiB 时仍应分段读取 |
| Phase 估算输入 | `<30K` token 为 low | medium/high 改用 compact + batch；critical 停止注入 |
| 文件分片 | 每片最多 50 文件 | 超过 16 片时分批串行，不增大单片 |
| 报告渲染 | 单文件默认 65,536 bytes | 输出索引并将详细内容分章节 |
| 外部命令 | 必须显式 timeout | 超时写结构化审计和 checkpoint |

## 强制控制

1. 每个 Phase 边界运行 `scripts/measure_context.py`，它只读取文件大小元数据。
2. 模式搜索使用 `scripts/safe_grep.py`，禁止把递归 grep 命中直接写入终端。
3. Recon 只向 Pi 提供 `scan-plan.summary.json`；不得读取完整路径 list。
4. ELF 使用 batch/checkpoint/resume。
5. Phase 3 禁止读取完整报告正文，只读取字节数、状态和 audit JSON。
6. 工具 stdout/stderr、findings、路径列表和报告正文必须写入 `security-reports/`。
7. Pi 无 subagent 能力时按维度串行执行，禁止递归启动 `pi`。

## 风险分类

`measure_context.py` 采用保守的 `bytes / 3` 估算：

- `low`：继续执行。
- `medium`：只读紧凑摘要。
- `high`：拆分下一 Phase，使用文件化 batch。
- `critical`：停止向模型注入，写 partial checkpoint，并按 `references/abort-recovery.md` 恢复。

`abort` 可能来自 provider、模型上下文、工具超时、用户取消或 runtime 异常，skill 不应假设所有 abort 都可由 Python 捕获，也不得把经验阈值描述为 Pi 的稳定 API 契约。
