---
name: security-scanner
description: >
  AI 辅助安全合规扫描工具。扫描软件包的 6 个维度：ELF 安全编译、公网地址、口令硬编码、
  未公开接口、敏感文件泄露、文件权限。支持 Claude Code / Codex / OpenCode。
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
9. **组件基础档案**（component_info）：架构类型、默认账号、个人数据、root 启动需求。

## 文件结构

```text
security-scanner/
├── SKILL.md
├── scanners/
│   ├── elf-scanner.md
│   ├── url-scanner.md
│   ├── secret-scanner.md
│   ├── comment-scanner.md
│   ├── fileleak-scanner.md
│   ├── permission-scanner.md
│   ├── crypto-scanner.md
│   ├── network-scanner.md
│   └── component-info-scanner.md
├── orchestration/
│   ├── orchestrator.md
│   ├── reconnaissance.md
│   └── reporter.md
├── references/
│   ├── allowlists.md
│   ├── checksec-guide.md
│   ├── dependency-check.md
│   └── verdict-rules.md
└── templates/
    ├── report-comprehensive.md
    ├── report-安全编译.md
    ├── report-公网地址.md
    ├── report-口令硬编码.md
    └── report-未公开接口.md
```

## 执行流程

严格按以下顺序执行。每个 Phase 只在需要时加载对应模块，保证渐进式披露。

渐进式披露路径：

```text
SKILL.md
├── Phase -1 -> references/dependency-check.md
├── Phase 0  -> orchestration/reconnaissance.md
├── Phase 1  -> scanners/*.md（仅加载适用维度）
   - 新增: scanners/crypto-scanner.md
   - 新增: scanners/network-scanner.md
   - 新增: scanners/component-info-scanner.md
├── Phase 2  -> references/verdict-rules.md
└── Phase 3  -> orchestration/reporter.md
              -> templates/report-comprehensive.md
              -> templates/report-安全编译.md
              -> templates/report-公网地址.md
              -> templates/report-口令硬编码.md
              -> templates/report-未公开接口.md
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

### Phase 1: 并行扫描（9 个维度）

根据 Scan Plan 按需加载 scanner 模块并派发 subagent。

派发策略：

- 每个 subagent 只加载自己负责的 scanner `.md` 文件。
- subagent 上下文只包含自身扫描规则、分配文件列表、必要白名单和输出 schema。
- 不包含其他维度规则或其他 agent 中间结果。

按需派发：

1. **ELF Scanner**：读取 `scanners/elf-scanner.md`，输入 `elf_files`；ELF 文件 >20 个时分片。
2. **URL Scanner**：读取 `scanners/url-scanner.md` 和 `references/allowlists.md`，输入 `source_shards + config_files`。
3. **Secret Scanner**：读取 `scanners/secret-scanner.md`，输入 `source_shards + config_files`。
4. **Comment Scanner**：读取 `scanners/comment-scanner.md`，输入 `source_shards`。
5. **FileLeak Scanner**：读取 `scanners/fileleak-scanner.md`，输入完整文件列表（`all_files`）。
   - 按文件名模式匹配检测敏感文件泄露。
   - 文件数量超过 5000 时仅按文件名匹配，不做内容确认分析。
   - 降级时跳过 LOW/MEDIUM/INFO 风险模式，仅检查 HIGH 风险文件。

6. **Permission Scanner**：读取 `scanners/permission-scanner.md`，输入完整文件列表（`all_files`）。
   - 检查 setuid/setgid、world-writable、异常可执行权限。
   - 自动排除虚拟文件系统、挂载点和特殊文件类型。
   - `stat` 不可用时使用 `ls -la` 解析；大规模扫描时仅检查 ELF 和脚本文件。
7. **Crypto Scanner**：读取 `scanners/crypto-scanner.md`、`references/patterns-crypto.md`、`references/red-line-rules.md`、`references/library-vuln-caps.md`，输入 `source_shards + config_files + dependency_files`。
8. **Network Scanner**：读取 `scanners/network-scanner.md`、`references/patterns-network.md`，输入 `source_shards + config_files`。
9. **Component-Info Scanner**：读取 `scanners/component-info-scanner.md`、`references/personal-data-patterns.md`，输入 `source_shards + config_files + docker_files`。

等待所有 Scanner 完成后执行审计点 A1。

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

去重说明：crypto-scanner 与 secret-scanner 共享同一份凭证字符串匹配结果时，secret-scanner 优先（其严重度模型更精细）；crypto-scanner 仅保留算法/协议相关的 finding，凭证泄露细节由 secret-scanner 报告。

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
   - 4 份专项报告：安全编译、公网地址、口令硬编码、未公开接口
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

**新维度 evidence 扩展**：crypto / network / component_info 维度的 finding 的 `evidence` 字段可包含库信息，格式：
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
