# 安全合规扫描器（Security Compliance Scanner）

面向 AI 编码工具的安全合规扫描 SKILL。它不是独立 CLI 程序，而是一组结构化 Markdown 指令文件，由 Claude Code、Codex、OpenCode 等 AI 编码助手按阶段加载并执行。

## 项目简介

本 SKILL 用于对源码、配置、脚本、交付包和 ELF 二进制文件进行六维度安全合规检查，并生成简体中文报告。

适用场景：

| 场景 | 说明 |
|------|------|
| 开发者自检 | 在提交或交付前发现明显安全合规问题 |
| 安全审计 | 对交付包进行结构化复核 |
| AI 辅助审查 | 由 AI agent 编排预检、侦察、扫描、裁决和报告 |

支持目标：

- C/C++、Go、Python、Shell、Java、JavaScript、YAML/XML/JSON 等源码和配置。
- 源码 + ELF 二进制混合目录。
- 包含脚本、证书、日志、临时文件的交付包目录。

## 扫描维度

| # | 维度 | 检查内容 |
|---|------|----------|
| 1 | ELF 安全编译 | Stack Canary、NX、RELRO、PIE、BIND_NOW、Strip、RPATH/RUNPATH、FORTIFY_SOURCE |
| 2 | 公网地址 | 硬编码公网 URL、IP、域名、邮箱；HTTP 明文外部地址 |
| 3 | 口令和硬编码 | 明文密码、API Key、Token、私钥、编码凭证、配置文件凭证 |
| 4 | 未公开接口 | 大段注释中的隐藏调试能力、未公开接口、后门说明、敏感内部信息 |
| 5 | 敏感文件泄露 | `.env`、私钥、证书密钥、日志、临时文件、备份文件、core dump |
| 6 | 文件权限 | setuid/setgid、world-writable、异常可执行脚本 |

## 系统要求

### 必需环境

- 一个能加载 SKILL 的 AI 编码工具。
- 用户提供待扫描目标路径。
- 基础 shell 环境。

### 外部工具

预检阶段会检测工具并按降级链处理：

| 工具 | 用途 | 级别 |
|------|------|------|
| `grep` | 文本搜索 | 核心 |
| `find` | 文件发现 | 核心 |
| `file` | 文件类型识别 | 重要 |
| `stat` | 权限检查 | 重要 |
| `checksec` | ELF 安全编译检查 | ELF 维度核心 |
| `readelf` / `objdump` | ELF 降级检查 | 降级备选 |
| `xxd` / `od` | ELF magic bytes 检测 | 降级备选 |
| `python3` | 注释提取和复杂解析 | 可选/降级备选 |

`checksec` 不可用时，ELF Scanner 会尝试使用 `readelf`、`objdump`、`file` 等方案降级。缺少核心工具时，扫描会进入 blocked 状态并输出安装建议。

## 使用方式

将 `security-scanner/` 目录放在 AI 编码工具可读取的位置后，在对话中提出扫描请求即可。

示例：

```text
请对 /path/to/project 进行安全扫描
```

```text
扫描当前目录的口令硬编码和公网地址问题
```

```text
检查 /opt/package 中 ELF 文件的安全编译选项
```

本项目没有提供独立命令行入口。扫描执行由 AI agent 根据 `SKILL.md`、`orchestration/`、`scanners/`、`references/` 和 `templates/` 中的指令完成。

## 执行流程

```text
Phase -1: 环境预检
  -> 检测依赖、运行时和降级路径

Phase 0: 发现阶段
  -> 探索目录、排除第三方/生成代码、分类文件、生成 Scan Plan

Phase 1: 并行扫描
  -> 按需派发 6 个维度 Scanner subagent

Phase 2: 裁决阶段
  -> 对中低置信度 findings 进行上下文复核

Phase 3: 报告生成
  -> 输出终端摘要、JSON、综合报告和 4 份专项报告
```

审计检查点：

| 检查点 | 阶段 | 重点 |
|--------|------|------|
| A0 | Recon | 覆盖率、分片大小、目录完整性 |
| A1 | Scan | scanner 完成状态、schema 合规性、失败阈值 |
| A2 | Verdict | `confidence`、`verdict`、`verdict_reasoning` 完整性 |
| A3 | Report | 字段完整性、数据一致性、内容质量、覆盖完整性 |

## 输出格式

Reporter 指令定义三类输出：

| 输出 | 文件名模式 |
|------|------------|
| 终端摘要 | 直接输出扫描统计、严重度统计、裁决统计和报告路径 |
| JSON 结构化数据 | `security-scan-report-{component_name}-{date}.json` |
| 综合 Markdown 报告 | `security-scan-report-{component_name}-{date}.md` |
| 安全编译专项报告 | `report-安全编译-{component_name}-{date}.md` |
| 公网地址专项报告 | `report-公网地址-{component_name}-{date}.md` |
| 口令硬编码专项报告 | `report-口令硬编码-{component_name}-{date}.md` |
| 未公开接口专项报告 | `report-未公开接口-{component_name}-{date}.md` |

具体落盘位置由执行扫描的 AI agent 和用户当前工作目录决定；当前 SKILL 不强制固定 `reports/` 目录。

### Finding Schema

所有 Scanner、Verdict 和 Reporter 使用统一 finding schema：

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
  "detail": "NX 位未设置，堆栈可执行，存在安全风险",
  "suggestion": "编译时添加 -Wl,-z,noexecstack 链接参数",
  "evidence": "checksec 输出: NX disabled"
}
```

字段约束：

| 字段 | 说明 |
|------|------|
| `dimension` | `elf`、`url`、`secret`、`comment`、`file_leak`、`permission` |
| `line` | 源码行号为 integer；注释范围可为 string，如 `"36-50"`；不适用为 `null` |
| `status` | `PASS`、`WARN`、`FAIL` |
| `severity` | `critical`、`high`、`medium`、`low`、`info` |
| `confidence` | `high`、`medium`、`low` |
| `verdict` | `confirmed`、`suspected`、`rejected`、`needs_human`、`unverified` |

## 项目结构

```text
security-scanner/
├── README.md
├── SKILL.md
├── scanners/
│   ├── elf-scanner.md
│   ├── url-scanner.md
│   ├── secret-scanner.md
│   ├── comment-scanner.md
│   ├── fileleak-scanner.md
│   └── permission-scanner.md
├── orchestration/
│   ├── orchestrator.md
│   ├── reconnaissance.md
│   └── reporter.md
├── references/
│   ├── allowlists.md
│   ├── checksec-guide.md
│   ├── dependency-check.md
│   └── verdict-rules.md
├── templates/
│   ├── report-comprehensive.md
│   ├── report-安全编译.md
│   ├── report-公网地址.md
│   ├── report-口令硬编码.md
│   └── report-未公开接口.md
└── tests/
    └── fixtures/
        ├── elf-test/
        ├── source-test/
        ├── fileleak-test/
        ├── permission-test/
        └── expected/
```

## 配置与自定义

### 白名单和排除规则

编辑 `references/allowlists.md` 可以扩展：

- 标准协议命名空间白名单，如 W3C、SOAP、OASIS。
- 语言/框架强制引用白名单，如 Go import、npm/PyPI/Maven 仓库引用。
- 回环地址和 RFC 1918 私有地址规则。
- 第三方、生成代码和构建产物排除规则。
- 项目自定义白名单和排除项。

### 降级策略

降级策略集中在：

- `references/dependency-check.md`
- `orchestration/orchestrator.md`
- 各维度 scanner 的“异常处理”或“降级策略”段落

典型降级包括：

- `checksec` -> `readelf` / `objdump`
- `file` -> ELF magic bytes 检测
- `stat` -> `ls -la` 权限字符串解析
- 大规模目录 -> 只检查高风险模式或按分片扫描

## 测试夹具

测试夹具位于 `tests/fixtures/`：

| 路径 | 用途 |
|------|------|
| `elf-test/compile-test.sh` | 在 Linux/ELF 工具链环境下生成不同安全属性的 ELF 样本 |
| `source-test/url-test-samples.go` / `.py` | URL、IP、邮箱提取和白名单过滤样本 |
| `source-test/secret-test-samples.py` / `config-test.yaml` | 口令、密钥、私钥和配置凭证样本 |
| `source-test/comment-test-samples.c` | 长注释、隐藏调试和未公开接口样本 |
| `source-test/full-test/` | 覆盖 URL、Secret、Comment、FileLeak、Permission 的端到端小项目 |
| `fileleak-test/setup-fileleak.sh` | 生成敏感文件泄露测试目录 |
| `permission-test/setup-permissions.sh` | 生成权限异常测试目录 |
| `expected/*.json` | 各维度预期结果 baseline |

可运行的轻量校验：

```bash
bash -n security-scanner/tests/fixtures/elf-test/compile-test.sh
bash -n security-scanner/tests/fixtures/fileleak-test/setup-fileleak.sh
bash -n security-scanner/tests/fixtures/permission-test/setup-permissions.sh
python3 -m json.tool security-scanner/tests/fixtures/expected/url-expected.json >/dev/null
```

注意：`elf-test/compile-test.sh` 需要能生成 ELF 的 Linux 工具链。macOS 默认 Clang/GCC 不能生成 Linux ELF，运行完整 ELF fixture 时可能失败。

## 常见问题

### 这是可执行扫描器吗？

不是。它是 SKILL 指令包，由 AI agent 读取指令、执行 shell 命令、派发 subagent、汇总结果并生成报告。

### 可以只扫一个维度吗？

可以。用户可以在自然语言中指定维度，例如“只检查口令硬编码和公网地址”。Agent 应只加载相关 scanner 和必要 reference 文件。

### 报告一定会包含 6 个专项报告吗？

不是。当前设计要求生成 1 份综合报告、1 份 JSON 和 4 份专项报告：安全编译、公网地址、口令硬编码、未公开接口。FileLeak 和 Permission 的 findings 会进入 JSON 与综合报告。

### 低置信度发现如何处理？

中低置信度 findings 进入 Verdict 阶段，最终标记为 `confirmed`、`suspected`、`rejected`、`needs_human` 或 `unverified`。`needs_human` 和 `unverified` 必须在报告中明确标注。

## 说明

本项目用于安全合规审计辅助。AI 扫描结果可能存在误报或遗漏，`critical`、`high`、`needs_human`、`unverified` 结果应结合人工复核后处理。
