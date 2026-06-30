# 安全合规扫描器（Security Compliance Scanner）

面向 AI 编码工具的安全合规扫描 SKILL。它不是独立 CLI 程序，而是一组结构化 Markdown 指令文件，由 Claude Code、Codex、OpenCode 等 AI 编码助手按阶段加载并执行。

## 项目简介

本 SKILL 用于对源码、配置、脚本、交付包和 ELF 二进制文件进行九维度安全合规检查，并生成简体中文报告。

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
| 7 | 密码学合规 | 对称/非对称/Hash 算法、伪加密、随机数 API、不安全协议、库版本知识库匹配 |
| 8 | 网络协议与端口 | 通信协议（SSHv2/TLS1.2/TLS1.3）、监听端口、声明 vs 实际对账 |
| 9 | 组件基础档案 | 架构类型、默认账号、个人数据处理、root 启动需求、声明 vs 实际对账 |

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

Phase 1: registry 调度扫描
  -> discover_scanners() 自动发现 scanner
  -> topological_order() 按 consumes 依赖排序
  -> 通过 ScanContext 在 scanner 间中转 findings

Phase 2: 裁决阶段
  -> 对中低置信度 findings 进行上下文复核

Phase 3: 报告生成
  -> 输出终端摘要、JSON、综合报告和 7 份专项报告
```

Phase 1 采用 γ-sidecar（gamma sidecar）结构调度 scanner：每个维度都是 `scanners/<dim>/` 下的一组旁挂文件，由 `scanner.md`、`meta.yaml` 和可选 `references/` 组成。Registry 只发现目录，不维护旧式 flat scanner path；新增 scanner 即 drop a directory，让 `discover_scanners()` 读取新目录中的 `meta.yaml` 和 `scanner.md`。

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
| 密码学专项报告 | `report-密码学-{component_name}-{date}.md` |
| 网络专项报告 | `report-网络-{component_name}-{date}.md` |
| 组件档案专项报告 | `report-组件档案-{component_name}-{date}.md` |
| 组件档案 summary JSON | `component-info-summary-{component_name}-{date}.json` |

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
| `dimension` | `elf`、`url`、`secret`、`comment`、`file_leak`、`permission`、`crypto`、`network`、`component-info` |
| `line` | 源码行号为 integer；注释范围可为 string，如 `"36-50"`；不适用为 `null` |
| `status` | `PASS`、`WARN`、`FAIL` |
| `severity` | `critical`、`high`、`medium`、`low`、`info` |
| `confidence` | `high`、`medium`、`low` |
| `verdict` | `confirmed`、`suspected`、`rejected`、`needs_human`、`unverified` |

## 项目结构

当前项目采用 γ-sidecar（gamma sidecar）布局：每个 scanner 位于 `scanners/<dim>/`，目录内包含 `scanner.md`、`meta.yaml`，并可按需附带 `references/`。新增维度时只需放入一个新的 `scanners/<dim>/` 目录，不需要增加扁平化 scanner 文件路径或手工修改调度列表。

```text
security-scanner/
├── README.md
├── SKILL.md
├── component-info.md
├── scanners/
│   ├── __init__.py
│   ├── registry/
│   │   ├── __init__.py
│   │   ├── schema.py
│   │   ├── resolver.py
│   │   ├── context.py
│   │   └── tokens.py
│   ├── elf/
│   │   ├── meta.yaml
│   │   ├── scanner.md
│   │   └── references/checksec-guide.md
│   ├── url/
│   │   ├── meta.yaml
│   │   └── scanner.md
│   ├── secret/
│   │   ├── meta.yaml
│   │   └── scanner.md
│   ├── comment/
│   │   ├── meta.yaml
│   │   └── scanner.md
│   ├── fileleak/
│   │   ├── meta.yaml
│   │   └── scanner.md
│   ├── permission/
│   │   ├── meta.yaml
│   │   └── scanner.md
│   ├── network/
│   │   ├── meta.yaml
│   │   ├── scanner.md
│   │   └── references/patterns-network.md
│   ├── crypto/
│   │   ├── meta.yaml
│   │   ├── scanner.md
│   │   └── references/patterns-crypto.md
│   └── component-info/
│       ├── meta.yaml
│       ├── scanner.md
│       ├── references/architecture-signals.md
│       └── references/personal-data-patterns.md
├── orchestration/
│   ├── orchestrator.md
│   ├── reconnaissance.md
│   └── reporter.md
├── references/
│   ├── allowlists.md
│   ├── dependency-check.md
│   ├── verdict-rules.md
│   ├── library-vuln-caps.md
│   └── red-line-rules.md
├── templates/
│   ├── report-comprehensive.md
│   ├── report-安全编译.md
│   ├── report-公网地址.md
│   ├── report-口令硬编码.md
│   ├── report-未公开接口.md
│   ├── report-密码学.md
│   ├── report-网络.md
│   └── report-组件档案.md
└── tests/
    ├── fixtures/
    └── test_*.py
```

## 配置与自定义

### 扩展新维度

新增 scanner 只需要按 γ-sidecar 结构创建 `scanners/<new-dim>/`，并在其中放置 `meta.yaml`、`scanner.md` 和可选 `references/`。Phase 1 由 `discover_scanners()` 自动发现维度，并由 `topological_order()` 根据 `meta.yaml` 中的 `consumes` 依赖决定调度顺序，不需要维护硬编码 scanner 列表；新增 scanner 即 drop a directory。

如果新维度需要消费上游 findings，在 `meta.yaml` 中声明 `consumes`，并使用 `inject_as: data`、`severity_filter` 和 `token_budget` 控制注入方式、严重度范围和 token 预算。上游 findings 经 `ScanContext` 中转后作为 data 注入下游 scanner 的 user message，不写入 system prompt。

本地 reference 放在 `scanners/<dim>/references/` 并以相对路径引用；跨维度和跨阶段共享 reference 放在顶层 `references/`。当前共享关系与 `scanners/*/meta.yaml` 保持一致：

| 共享 reference | 引用者 |
|----------------|--------|
| `references/allowlists.md` | `comment`、`url`、`secret`、`fileleak`、`permission`、`elf`、`network`、`crypto`、`component-info`（9 个 scanner 全部引用） |
| `references/red-line-rules.md` | `network`、`crypto`、`component-info` |
| `references/library-vuln-caps.md` | `network`、`crypto` |
| `references/dependency-check.md` | `orchestration/orchestrator.md` 在 Phase -1 环境预检中加载 |
| `references/verdict-rules.md` | 裁决阶段（Phase 2）由 orchestration 流程加载 |

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
| `fileleak-test/setup-fileleak.sh` | 生成敏感文件泄露测试目录 |
| `permission-test/setup-permissions.sh` | 生成权限异常测试目录 |
| `crypto-test/` | 密码学算法、随机数 API、不安全协议和库依赖样本 |
| `network-test/` | 网络协议、监听端口、TLS/SSH 配置和声明对账样本 |
| `component-info-test/` | 组件基础档案单维度样本，覆盖架构、默认账号、个人数据和 root 需求信号 |
| `source-test/full-test/` | 覆盖 URL、Secret、Comment、FileLeak、Permission 的端到端小项目 |
| `full-test-component-info/` | 覆盖 component-info 综合对账和 summary 输出的端到端小项目 |
| `expected/url-expected.json` | 公网地址维度 baseline |
| `expected/secret-expected.json` | 口令和硬编码维度 baseline |
| `expected/comment-expected.json` | 未公开接口维度 baseline |
| `expected/fileleak-expected.json` | 敏感文件泄露维度 baseline |
| `expected/permission-expected.json` | 文件权限维度 baseline |
| `expected/elf-expected.json` | ELF 安全编译维度 baseline |
| `expected/crypto-expected.json` | 密码学合规维度 baseline |
| `expected/network-expected.json` | 网络协议与端口维度 baseline |
| `expected/component-info-expected.json` | 组件基础档案 findings baseline |
| `expected/component-info-summary-expected.json` | 组件基础档案 summary JSON baseline |

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

不是。当前设计要求生成 1 份综合报告、1 份 JSON 和 7 份专项报告：安全编译、公网地址、口令硬编码、未公开接口、密码学、网络、组件档案。FileLeak 和 Permission 的 findings 会进入 JSON 与综合报告。

### 低置信度发现如何处理？

中低置信度 findings 进入 Verdict 阶段，最终标记为 `confirmed`、`suspected`、`rejected`、`needs_human` 或 `unverified`。`needs_human` 和 `unverified` 必须在报告中明确标注。

### 9 个新维度和老的 6 个维度怎么协调？

crypto / network / component-info 三个新维度是 6 维度的扩展，不是替代。`crypto` 与 `secret` 维度共享凭证字符串匹配结果时，`secret` 优先（其严重度模型更精细）；`crypto` 仅保留算法/协议相关 finding，凭证泄露细节由 `secret` 报告。新维度的 evidence 字段可包含库信息，老 6 维度不解析该格式。

### 综合报告为什么有"组件档案概览"章节？

为防止报告爆炸（中型项目可能有 200+ finding），综合报告顶部插入一个不带文件/行号的概览表，链接到 3 个详细子报告。审计员先看概览判断有无重大问题，再按需展开子报告。

### 推断不出的字段怎么填？

每字段都有 AUTO/INFERRED/MISSING 三种标签：
- AUTO = 多源验证高置信度
- INFERRED = 有信号但弱
- MISSING = 机扫无信号，必须人工补全
MISSING 字段在 summary JSON 中保留但 value 为空，在 Markdown 报告中以"不适用"或"待人工补全"展示。

## 说明

本项目用于安全合规审计辅助。AI 扫描结果可能存在误报或遗漏，`critical`、`high`、`needs_human`、`unverified` 结果应结合人工复核后处理。
