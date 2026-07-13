---
name: security-scanner
description: >
  AI 辅助安全合规扫描工具。扫描软件包的 13 个维度：ELF 安全编译、公网地址、口令硬编码、
  未公开接口、敏感文件泄露、文件权限、密码学合规、网络协议与端口、组件基础档案、
  依赖组件风险、安全编码规范、完整性校验、内容合规。支持 Claude Code / Codex / OpenCode / Pi Agent。
compatibility: Requires Python 3.10+ and PyYAML; external scanner tools are checked during preflight and may use documented degradation paths.
triggers:
  - 安全扫描
  - 合规检查
  - 安全审计
  - 组件基础信息
  - 组件档案
  - 算法盘点
  - 端口扫描
  - security scan
  - compliance check
  - checksec
  - component info
  - algorithm audit
---

# 安全合规扫描器 (Security Compliance Scanner)

支持 Claude Code / Codex / OpenCode / Pi Agent 时遵循同一共享报告契约：`scan_profile` 只影响 Phase 1 扫描调度，不影响 Phase 3 报告产物数量；Phase 3 必须生成最终汇总报告 + 13 个维度独立详细报告。

## 终端输出契约

默认采用最小终端输出：每个 Phase 最多输出 1 行终端状态，最终终端摘要最多 8 行。不得向终端输出完整 JSON、原始 findings、大段 stdout/stderr 或文件清单；完整数据必须写入 security-reports/ 下的 JSON、审计日志、Markdown 报告和维度报告。不得向用户回显已读文件全文。调试、失败、降级和审计细节写入结构化产物，不在终端展开。

## 触发条件

用户请求安全扫描 / 合规检查 / 安全审计，或 ELF / 公网地址 / 口令 / 未公开接口等专项检查时激活。用户必须提供扫描目标路径（相对路径先转为绝对路径）。

## Pi / 多 Harness 路径与能力约束

- 将已加载 `SKILL.md` 的父目录解析为绝对路径 `SKILL_ROOT`；bundled scripts、scanners、templates、references 均相对该目录定位，禁止假设当前目录就是 skill 目录。
- 将用户目标解析为绝对路径 `TARGET_ROOT`；默认报告目录为 `$TARGET_ROOT/security-reports/`（目标是包文件时使用其父目录）。
- Phase -1 先执行 `python3 "$SKILL_ROOT/scripts/pi_preflight.py" --target "$TARGET_ROOT"`。
- 若 harness 提供 subagent/session 能力，可使用独立 session；否则在当前 Pi session 中按维度串行执行并逐维写 checkpoint。禁止递归启动 `pi` 模拟 subagent。

## 扫描维度

1. **ELF 安全编译**（elf）
2. **公网地址**（url）
3. **口令和硬编码**（secret）
4. **未公开接口**（comment）
5. **敏感文件泄露**（fileleak）
6. **文件权限**（permission）
7. **密码学合规**（crypto）
8. **网络协议与端口**（network）
9. **组件基础档案**（component-info）
10. **依赖组件风险**（dependency）
11. **安全编码规范**（secure-coding）
12. **完整性校验**（integrity）
13. **内容合规**（content-compliance）

## Scan Profiles

未显式指定时默认 `redline-full`。非法 profile 必须 `FAIL` 并停止进入 Phase 1。实际执行 = `discover_scanners()` ∩ profile；未发现维度记为覆盖缺口，不得虚构 scanner。

| Profile | 维度范围 |
|---------|----------|
| `redline-p0` | elf、url、secret、comment、fileleak、permission、crypto、network、component-info、dependency |
| `redline-full` | 全部 13 维（默认） |
| `redline-binary` | elf、fileleak、permission、dependency |

scan_profile 只影响 Phase 1 扫描调度，不影响 Phase 3 报告产物数量

## 渐进式披露（强制）

激活后只读本文件与 `orchestration/router.md`。激活时禁止读取完整 `orchestration/orchestrator.md`；每个 Phase **只在需要时**定位并分段读取对应小节或阶段文件。禁止预读全部 scanners、templates、`redline-spec.md`。

```text
SKILL.md（本文件）-> orchestration/router.md（紧凑路由）
├── Phase -1 -> references/dependency-check.md
├── Phase -0 -> scripts/package_materializer.py（rpm2cpio/cpio/rpmbuild；可选 dnf/patch/tar）
├── Phase 0  -> orchestration/reconnaissance.md + normalize_shards.py + validate_shards.py + summarize_scan_plan.py
├── Phase 1  -> resolve_scanners.py + scanners/<dim>/{meta.yaml,scanner.md}
│              -> 仅 meta.references 声明的文件 + references/finding-schema.md
├── Phase 2  -> references/verdict-rules.md + references/finding-schema.md
└── Phase 3  -> orchestration/reporter.md + templates/report-manifest.yaml
               -> templates/*（按 manifest）+ references/redline-mapping.md
               -> references/redline-spec.md（仅 A3b/综合报告）
```

调度细节、审计点、条件跳过、降级矩阵：见 `orchestration/orchestrator.md`。
Finding 字段定义：见 `references/finding-schema.md`（勿在此内嵌全文）。
Pi 安全阈值与中断恢复：见 `references/agent-runtime-limits.md`、`references/abort-recovery.md`（仅风险或恢复时加载）。
人读安装与目录树：见 `README.md`（运行时 agent 不读）。

### 硬性禁止

- 不得在激活时加载任意 `scanners/*/scanner.md` 或全部 templates。
- scanner 的独立或逻辑 session 不得加载其他维 `scanner.md`、全量 findings、`redline-spec.md`。
- 上游 findings 经 `ScanContext.consume(..., compact=True)` 注入 user message，不得写入 system prompt。

## 异常处理总则

1. 永不丢失已完成工作。
2. 部分结果优于无结果。
3. 透明失败，失败和降级必须在最终报告标注。
4. 每个 subagent 须有超时、错误、空结果处理；最多重试 2 次，退避 0s、5s、15s。

## 报告语言

所有报告、说明、发现详情、修复建议、裁决理由均以**简体中文**编写。

## 报告渲染约束（强制）

- 模板占位符统一为 `[[UPPER_SNAKE_CASE]]` 双中括号格式（如 `[[COMPONENT_NAME]]`）。
- **禁止使用 f-string 或 `.format()` 渲染模板**——`{}` 在模板里会与 f-string 冲突，未定义变量会触发 `NameError`。
- 每个 Phase 边界必须调用 `$SKILL_ROOT/scripts/measure_context.py`；`risk=critical` 时停止模型注入并写 partial checkpoint。
- Phase 1 模式搜索必须调用 `$SKILL_ROOT/scripts/safe_grep.py`；路径清单使用 `--files-file/--base-root`，禁止把递归 grep 命中行直接写入终端上下文。
- 禁止对 `scanners/registry` 目录调用 `read` 或 `cat *`；必须使用 `$SKILL_ROOT/scripts/resolve_scanners.py`。
- 内容合规规则只允许由 `$SKILL_ROOT/scripts/content_compliance_probe.py` 在本地加载，规则原文和 raw evidence 不得注入模型。
- Phase 3 报告生成必须先调用 `$SKILL_ROOT/scripts/build_report_values.py`，再调用 `$SKILL_ROOT/scripts/render_template.py`，完成后必须调用 `$SKILL_ROOT/scripts/audit_render.py` 校验（详见 `references/render-audit.md` 的 A4 审计点）。
- 必填占位符缺失时 `--strict` 模式返回非零退出码；非 strict 模式下缺失保留为 `[[NAME]]` 字面量并写入 `*.missing.json` 供审计追溯。
- 缺失必填占位符连续 2 次渲染仍失败时，报告状态必须记为 `degraded` 并在 `audit_log` 中保留追溯记录。
