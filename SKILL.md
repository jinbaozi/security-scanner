---
name: security-scanner
description: >
  AI 辅助安全合规扫描工具。扫描软件包的 9 个维度：ELF 安全编译、公网地址、口令硬编码、
  未公开接口、敏感文件泄露、文件权限、密码学合规、网络协议与端口、组件基础档案。
  支持 Claude Code / Codex / OpenCode。
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

## 触发条件

当用户请求对代码或软件包进行以下操作时激活本 SKILL：

- 安全扫描 / 安全合规检查 / 安全审计
- ELF 安全编译检查
- 公网地址扫描 / 硬编码检查
- 口令扫描 / 密钥扫描
- 未公开接口扫描

用户必须提供扫描目标路径。路径可以是绝对路径；若用户提供相对路径，先转换为绝对路径再进入流程。

## 扫描维度

1. **ELF 安全编译**：栈保护、NX、RELRO、PIE、BIND_NOW、Strip、RPATH、FORTIFY_SOURCE。
2. **公网地址**：硬编码公网 IP、URL、域名、邮箱。
3. **口令和硬编码**：密码、密钥、Token、私钥等硬编码凭证。
4. **未公开接口**：大段注释中隐藏的未文档化功能或接口。
5. **敏感文件泄露**：`.env`、私钥、日志、临时文件等交付包污染。
6. **文件权限**：setuid/setgid、world-writable、异常可执行权限。
7. **密码学合规**（crypto）：对称/非对称/Hash 算法、伪加密、随机数 API、不安全协议。
8. **网络协议与端口**（network）：通信协议（SSHv2/TLS1.2/TLS1.3 等）、监听端口。
9. **组件基础档案**（component-info）：架构类型、默认账号、个人数据、root 启动需求。

## 文件结构

本 SKILL 使用 γ-sidecar（gamma sidecar）结构组织 scanner：每个维度位于 `scanners/<dim>/`，由 `scanner.md`、`meta.yaml` 和可选 `references/` 组成。新增 scanner 即 drop a directory；registry 发现的是维度目录，不使用旧式扁平 scanner 文件路径。

```text
security-scanner/
├── SKILL.md
├── scanners/
│   ├── __init__.py
│   ├── registry/
│   │   ├── __init__.py
│   │   ├── schema.py
│   │   ├── resolver.py
│   │   ├── context.py
│   │   └── tokens.py
│   ├── elf/{meta.yaml,scanner.md}
│   ├── url/{meta.yaml,scanner.md}
│   ├── secret/{meta.yaml,scanner.md}
│   ├── comment/{meta.yaml,scanner.md}
│   ├── fileleak/{meta.yaml,scanner.md}
│   ├── permission/{meta.yaml,scanner.md}
│   ├── network/{meta.yaml,scanner.md}
│   ├── crypto/{meta.yaml,scanner.md}
│   └── component-info/{meta.yaml,scanner.md}
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
└── templates/
    ├── report-comprehensive.md
    ├── report-安全编译.md
    ├── report-公网地址.md
    ├── report-口令硬编码.md
    ├── report-未公开接口.md
    ├── report-密码学.md
    ├── report-网络.md
    └── report-组件档案.md
```

## 执行流程

严格按以下顺序执行。每个 Phase 只在需要时加载对应模块，保证渐进式披露。

渐进式披露路径：

```text
SKILL.md
├── Phase -1 -> references/dependency-check.md
├── Phase 0  -> orchestration/reconnaissance.md
├── Phase 1  -> discover_scanners() 自动发现 scanners/<dim>/{meta.yaml,scanner.md}
│              -> topological_order() 按 consumes 依赖调度
│              -> ScanContext 中转 scanner findings
├── Phase 2  -> references/verdict-rules.md
└── Phase 3  -> orchestration/reporter.md
              -> templates/report-comprehensive.md
              -> templates/report-安全编译.md
              -> templates/report-公网地址.md
              -> templates/report-口令硬编码.md
              -> templates/report-未公开接口.md
              -> templates/report-密码学.md
              -> templates/report-网络.md
              -> templates/report-组件档案.md
```

### Phase -1: 环境预检

1. 读取 `references/dependency-check.md`。
2. 执行环境预检：检测运行时、检查依赖。
3. 若检测到缺失工具：
   a. **阻断执行**，使用 `question` 工具向用户展示缺失工具列表及安装方法。
   b. 让用户选择：手动安装 / 自动安装 / 接受降级。
   c. 用户选择自动安装时，尝试自动安装缺失依赖。
   d. 安装失败时，使用 `question` 工具询问用户是否接受降级模式。
   e. 用户拒绝降级 → `blocked`，终止扫描并输出安装指南。
4. 生成依赖报告：`ready` / `degraded` / `blocked`。
   - `degraded` 仅在用户明确同意降级后才设置。
5. `ready` 或 `degraded`（用户已同意）时输出摘要并进入 Phase 0。

终端摘要：

```text
Phase -1: 环境预检 PASS
  环境状态: ready | degraded
  可用工具: grep, find, file, stat, checksec
  降级项: [列出降级项]
```

### Phase 0: 发现阶段（Reconnaissance）

1. 读取 `orchestration/reconnaissance.md`。
2. 派发 Recon subagent 执行目录探索、文件分类和分片。
3. 获取 Scan Plan JSON。
4. 执行审计点 A0：覆盖率、分片大小、目录完整性。
5. 审计通过后输出发现摘要并进入 Phase 1。

终端摘要：

```text
Phase 0: 发现阶段 PASS
  目标: /path/to/project
  组件名: {component_name}
  总文件数: 1234 | ELF: 12 | 源码: 1100 | 配置: 122
  排除: 50 个文件（第三方/生成代码）
  分片数: 3
```

### Phase 1: registry 调度扫描（9 个维度）

根据 Scan Plan 和 scanner registry 按需加载 scanner 模块并派发 9 个独立 LLM session（Q21B）。

Phase 1 依赖 γ-sidecar（gamma sidecar）布局：每个 scanner 是 `scanners/<dim>/` 目录中的 `scanner.md` + `meta.yaml` + 可选 `references/`。新增维度只需 drop a directory，调度器通过目录发现和 `meta.yaml` 依赖声明完成加载、排序和 reference 注入。

调度策略：

- 调用 `discover_scanners()` 自动发现 `scanners/<dim>/meta.yaml` 和 `scanners/<dim>/scanner.md`。
- 调用 `topological_order()` 根据各 scanner `meta.yaml` 的 `consumes` 依赖生成调度顺序；无依赖且资源允许的维度可并行执行。
- 每个 scanner session 只加载自身 `scanner.md`、分配文件列表、输出 schema，以及 `meta.yaml` 声明的 references。
- scanner 间 findings 通过 `ScanContext` 中转。若下游 `meta.yaml` 声明 `consumes`，上游 findings 按 `inject_as: data`、`severity_filter`、`token_budget` 筛选后注入下游 user message，不能写入 system prompt。
- 维度专属 references 保留在 `scanners/<dim>/references/`；顶层 `references/` 用于跨维度和跨阶段共享资料。当前共享关系与 `scanners/*/meta.yaml` 保持一致：
  - `references/allowlists.md`：`comment`、`url`、`secret`、`fileleak`、`permission`、`elf`、`network`、`crypto`、`component-info`（9 个 scanner 全部引用）。
  - `references/red-line-rules.md`：`network`、`crypto`、`component-info`。
  - `references/library-vuln-caps.md`：`network`、`crypto`。
  - `references/dependency-check.md`：`orchestration/orchestrator.md` 在 Phase -1 环境预检中加载。
  - `references/verdict-rules.md`：裁决阶段（Phase 2）由 orchestration 流程加载。

当前 registry 应发现以下 9 个维度：

1. `elf`：`scanners/elf/{meta.yaml,scanner.md}`
2. `url`：`scanners/url/{meta.yaml,scanner.md}`
3. `secret`：`scanners/secret/{meta.yaml,scanner.md}`
4. `comment`：`scanners/comment/{meta.yaml,scanner.md}`
5. `fileleak`：`scanners/fileleak/{meta.yaml,scanner.md}`
6. `permission`：`scanners/permission/{meta.yaml,scanner.md}`
7. `network`：`scanners/network/{meta.yaml,scanner.md}`
8. `crypto`：`scanners/crypto/{meta.yaml,scanner.md}`
9. `component-info`：`scanners/component-info/{meta.yaml,scanner.md}`

所有适用 Scanner 完成后执行审计点 A1。

失败处理：

- 单个 Agent 失败：重试最多 2 次，仍失败则标记维度 FAILED。
- 2-3 个 Agent 失败：部分降级，继续其他维度。
- >=4 个 Agent 失败：Phase 级降级，收集已完成结果。

### Phase 2: 裁决阶段（Verdict）

1. 读取 `references/verdict-rules.md`。
2. 收集所有 Scanner findings。
3. 高置信度 findings 直接通过。
4. 对中/低置信度 findings 派发 Verdict subagent。
5. 执行审计点 A2。

去重说明：`crypto` 与 `secret` 维度共享同一份凭证字符串匹配结果时，`secret` 优先（其严重度模型更精细）；`crypto` 仅保留算法/协议相关的 finding，凭证泄露细节由 `secret` 报告。

分批策略：

- <=20 条：单个 Verdict Agent。
- 21-100 条：按维度分组，每组一个 Verdict Agent。
- >100 条：每 20 条一批，优先处理高严重度。

### Phase 3: 报告生成

1. 读取 `orchestration/reporter.md`。
2. 读取 `templates/` 下报告模板。
3. 派发 Reporter subagent 生成：
   - 终端摘要
   - JSON 结构化数据
   - 综合 Markdown 报告
   - 7 份专项报告：安全编译、公网地址、口令硬编码、未公开接口、密码学、网络、组件档案
4. 执行审计点 A3：字段完整性、数据一致性、内容质量、覆盖完整性。

## Finding Schema

所有 Scanner 和 Verdict Agent 使用统一 finding 格式：

```json
{
  "id": "{DIMENSION}-{SEQ}",
  "dimension": "elf|url|secret|comment|file_leak|permission",
  "file": "文件绝对路径",
  "line": "integer | string | null — 源码行号、注释范围或不适用",
  "check_item": "检查项名称",
  "status": "PASS|WARN|FAIL",
  "severity": "critical|high|medium|low|info",
  "confidence": "high|medium|low",
  "verdict": "confirmed|suspected|rejected|needs_human|unverified",
  "verdict_reasoning": "裁决理由（简体中文，至少包含裁决依据和上下文判断）",
  "detail": "问题描述（简体中文）",
  "suggestion": "修复建议（简体中文）",
  "evidence": "证据（代码片段或命令输出）"
}
```

`line` 字段按维度解释：

| 维度 | line 类型 | 示例 |
|------|-----------|------|
| ELF | `null` | `null` |
| URL | `integer` | `45` |
| Secret | `integer` | `32` |
| Comment | `string` | `"36-50"` |
| FileLeak | `null` 或 `integer` | `null` |
| Permission | `null` | `null` |

**新维度 evidence 扩展**：crypto / network / component-info 维度的 finding 的 `evidence` 字段可包含库信息，格式：
`library=NAME@VERSION | library_version=VERSION | trigger=REASON | cve=CVE-XXXX-XXXXX`
老 6 维度不解析此格式。

## 异常处理总则

1. 永不丢失已完成工作。
2. 部分结果优于无结果。
3. 透明失败，所有失败和降级必须在最终报告中标注。
4. 每个 subagent 调用必须有超时、错误、空结果处理。
5. 每个 Agent 最多重试 2 次，退避时间为 0s、5s、15s。

## 报告语言

所有报告、说明、发现详情、修复建议、裁决理由均以**简体中文**编写。
