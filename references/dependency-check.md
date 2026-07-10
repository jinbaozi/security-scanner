# Phase -1: 环境预检（Pre-flight Check）

> Orchestrator 在 Phase 0 之前执行。工具状态模型以 `orchestration/orchestrator.md` 为准；本文件列出预检步骤与关键词，不重复展开长表。

## 职责边界

- Phase -1：检测运行环境与外部工具可用性。
- Dependency Scanner：项目依赖、锁文件、SBOM、公开漏洞。
- 缺少 lock/SBOM → Dependency 产出 `MISSING_LOCK_FILE`；Crypto/Network 不重复产出。

## 工具状态关键词

预检必须识别并记录：`available`、`missing`、`broken`、`invocation_error`、`parse_error`、`confirmed_unavailable`、`user_approved_degraded`。

`invocation_error/parse_error 不得静默降级`。任何 `degraded` 必须含 `unavailable_proof` 或 `user_approval_ref`（对应 `user_approved_degraded`）。

## 工具清单

| 级别 | 工具 | 用途 |
|------|------|------|
| 核心 | `grep`、`find` | 文本搜索与文件发现 |
| 重要 | `file`、`stat`、`checksec` | 类型、权限、ELF 加固 |
| 降级备选 | `readelf`、`objdump`、`xxd`、`od`、`python3` | ELF/解析降级 |
| RPM 物化 | `rpm2cpio`、`cpio`、`rpmbuild`、`patch`、`tar` | SRPM `%prep` / RPM 展开 |
| 可选 | `dnf` | 仅用户授权后的 `dnf builddep` |
| 可选 | `jq`、`xmllint` | 结构化解析；可降级到 python3 |

## 执行步骤

1. 检测运行时：`uname`、`python3`/`bash` 可用性。
2. 按上表 `which` 检查工具；记录 `available` / `missing` / `broken`。
3. 对 `checksec` 等二进制做一次 `--help` 或等价 probe；共享库缺失记 `broken`。
4. 可选：探测 NVD/OSV 可达性；不可达则 degraded 到内置 `library-vuln-caps.md`，不阻断。
5. 若核心/重要工具缺失：**阻断**，用 `question` 让用户选：手动安装 / 自动安装 / 接受降级。
6. 用户选自动安装时再检查 root/sudo；失败则再次询问是否接受降级。
7. 用户拒绝降级 → `blocked`，输出安装指南并终止。
8. 输出依赖报告：`ready` / `degraded`（须有 `user_approval_ref` / `user_approved_degraded`）/ `blocked`。

RPM 说明：`dnf` 缺失只影响 builddep 修复路径；扫描 `.src.rpm` 时缺少物化工具会导致 A-0 blocked。不得静默执行 `dnf builddep`。

## 终端摘要

```text
Phase -1: 环境预检 PASS status=ready|degraded missing_tools=N degraded_items=N
```

## 安装提示（按需展示）

- Fedora/RHEL: `sudo dnf install -y binutils file xxd python3 checksec`
- Debian/Ubuntu: `sudo apt install -y binutils file xxd python3`
- 物化额外：`rpm2cpio cpio rpm-build patch tar`

## 降级记录

任何 `degraded` 必须含 `unavailable_proof` 或 `user_approval_ref`。`confirmed_unavailable` 可用于技术降级；`invocation_error` / `parse_error` 不得写成 degraded。
