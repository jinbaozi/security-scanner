# Phase -1: 环境预检（Pre-flight Check）

> 本文件指导 Orchestrator 执行环境预检，检测和安装所需依赖。

## 执行时机

在 Phase 0（Reconnaissance）之前执行。由 Orchestrator 自身执行，无需派发 subagent。

## 与 Dependency Scanner 的职责边界

Phase -1 只负责检测运行环境和外部工具可用性；Dependency Scanner 负责扫描项目依赖、锁文件、SBOM 和公开漏洞风险。

- 缺少 `grep`/`find`/`file`/`stat`/`checksec` 等运行依赖：由 Phase -1 处理。
- 缺少项目 lock 文件或 SBOM：由 Dependency Scanner 输出 `MISSING_LOCK_FILE` WARN finding。
- OSV/grype/trivy 不可用：Phase -1 可记录外部工具降级；Dependency Scanner 继续使用 manifest/SBOM/内置证据并在 `audit_log` 标注 degraded。
- Crypto/Network 不重复产出 `MISSING_LOCK_FILE`，只消费 dependency 的 SBOM/漏洞上下文。

## 步骤

### Step 1: 检测运行时环境

```bash
uname -s
uname -m
for cmd in pip uv pip3 npm cargo apt yum dnf brew pacman; do
  which "$cmd" 2>/dev/null && echo "  -> $cmd 可用"
done
for cmd in python3 node bash; do
  which "$cmd" 2>/dev/null && echo "  -> $cmd 可用: $($cmd --version 2>&1 | head -1)"
done
```

### Step 2: 检查核心依赖

```bash
for tool in grep find; do
  if ! which "$tool" >/dev/null 2>&1; then
    echo "MISSING: $tool (核心依赖)"
  else
    echo "OK: $tool -> $(which "$tool")"
  fi
done

for tool in file stat checksec; do
  if ! which "$tool" >/dev/null 2>&1; then
    echo "MISSING: $tool (重要依赖 — 需要安装后才能继续)"
  else
    echo "OK: $tool -> $(which "$tool")"
  fi
done

for tool in readelf objdump xxd od python3; do
  if ! which "$tool" >/dev/null 2>&1; then
    echo "MISSING: $tool (降级备选)"
  else
    echo "OK: $tool -> $(which "$tool")"
  fi
done

for tool in rpm2cpio cpio rpmbuild patch tar; do
    if ! which "$tool" >/dev/null 2>&1; then
        echo "MISSING: $tool (RPM/SRPM 输入物化依赖 — 缺失时无法证明 SRPM %prep 覆盖)"
    else
        echo "OK: $tool -> $(which "$tool")"
    fi
done

if ! which dnf >/dev/null 2>&1; then
    echo "MISSING: dnf (SRPM builddep 修复路径 — 缺失不影响已满足依赖的 %prep)"
else
    echo "OK: dnf -> $(which dnf)"
fi

for tool in jq xmllint; do
    if ! which "$tool" >/dev/null 2>&1; then
        echo "MISSING: $tool (新维度依赖 — 缺失时降级到 python3 -c 'import json/xml.etree')"
    else
        echo "OK: $tool -> $(which $tool)"
    fi
done
```

### Step 4: 检查 NVD/OSV 可达性（可选）

```bash
# 检测 NVD 可达性（用于库版本知识库快照）
if curl -sSf --max-time 5 https://nvd.nist.gov/ >/dev/null 2>&1; then
    echo "OK: NVD 可达，将拉取最新快照"
else
    echo "DEGRADED: NVD 不可达，使用内置 library-vuln-caps.md 知识库"
fi

# 检测 OSV 可达性（备选）
if curl -sSf --max-time 5 https://api.osv.dev/ >/dev/null 2>&1; then
    echo "OK: OSV 可达"
else
    echo "DEGRADED: OSV 不可达"
fi
```

失败时记录到 `degraded_dimensions`：
- `crypto:library-vuln-caps` 标记为 degraded，回落内置知识库
- 网络拉取失败不阻断扫描

### Step 2.1: RPM/SRPM 物化依赖说明

- `rpm2cpio`、`cpio`、`rpmbuild`、`patch`、`tar` 用于 Phase -0 输入物化；扫描 `.src.rpm` 时缺失这些工具会导致 A-0 blocked，源码相关 redline 覆盖不得标为完整通过。
- `dnf` 只用于用户授权后的 `dnf builddep <spec>` 修复路径。不得在预检中静默执行 builddep；该命令会修改系统包环境。
- 如果需要执行 `dnf builddep` 且当前用户不是 root，必须先提示用户提供 root/sudo 授权或 root 密码，再重试 `%prep`。

### Step 3: 阻断通知（缺失依赖）

> ⚠️ **重要变更**：如果检测到 `grep`/`find`/`file`/`stat`/`checksec` 任一缺失，**必须阻断**，
> 先通知用户，等用户确认后再尝试安装。不得在未通知用户的情况下直接降级。

如果 Step 2 中发现有工具缺失，执行以下阻断流程：

```text
╔══════════════════════════════════════════════════════════════╗
║  🛑 安全扫描已阻断 — 缺少必要依赖                          ║
║                                                            ║
║  以下工具未安装：                                           ║
║    - {缺失工具1}  — {用途说明}                             ║
║    - {缺失工具2}  — {用途说明}                             ║
║                                                            ║
║  请选择：                                                   ║
║    [A] 我手动安装缺失工具后，回来继续扫描                    ║
║    [B] 请帮我自动安装缺失工具                                ║
║    [C] 我不想安装，直接以降级模式继续扫描（部分功能受限）    ║
║                                                            ║
║  安装指南（按系统）：                                       ║
║    Fedora:   sudo dnf install -y binutils file xxd python3  ║
║    Ubuntu:   sudo apt install -y binutils file xxd python3  ║
║    CentOS:   sudo yum install -y binutils file xxd python3  ║
║    macOS:    brew install binutils coreutils xxd python     ║
╚══════════════════════════════════════════════════════════════╝
```

必须使用 `question` 工具让用户选择，得到明确答复前不得继续执行。

- 用户选 [A]：提示用户安装完成后回复"已安装"，然后重新执行 Step 2 验证。
- 用户选 [B]：进入 Step 5（安装缺失依赖）。
- 用户选 [C]：记录用户已同意降级，跳过安装步骤，直接标记 `degraded`（用户确认）。

### Step 4: 检查二进制依赖的运行依赖

```bash
if which checksec >/dev/null 2>&1; then
  checksec_path=$(which checksec)
  which bash >/dev/null 2>&1 || echo "WARN: checksec 依赖 bash 但 bash 不可用"
  which readelf >/dev/null 2>&1 || echo "WARN: checksec 依赖 readelf (binutils) 但 readelf 不可用"
  if file "$checksec_path" | grep -q "ELF"; then
    ldd "$checksec_path" 2>/dev/null | grep "not found" && echo "WARN: checksec 有缺失的共享库"
  fi
  checksec --help >/dev/null 2>&1 && echo "OK: checksec 运行测试通过" || echo "FAIL: checksec 运行测试失败"
fi
```

### Step 5: 检查权限

安装核心依赖需要 root 权限。若当前用户不是 root，先检查是否有缺失的核心依赖，有则阻断扫描并提示用户提供 root 密码。

```bash
check_root_for_install() {
    if [ "$(id -u)" -ne 0 ]; then
        echo "当前用户非 root，无法自动安装系统依赖。"
        echo "请使用 root 用户执行，或运行："
        echo "  sudo -i"
        echo "  dnf install -y checksec binutils file xxd python3"
        echo ""
        echo "安装完成后，重新启动本扫描。"
        exit 1
    fi
}

# 仅在缺失 file/stat/checksec 等需要系统包管理器安装的依赖时检查权限
missing_system_tools=false
for tool in file stat checksec readelf objdump xxd python3; do
    if ! which "$tool" >/dev/null 2>&1; then
        missing_system_tools=true
        break
    fi
done
if [ "$missing_system_tools" = true ]; then
    check_root_for_install
fi
```

### Step 6: 安装缺失依赖（用户选择 [B] 时执行）

安装优先级：

1. 跨语言包管理器：`pip`/`uv`、`npm`、`cargo`
2. 系统包管理器：`apt`/`yum`/`dnf`/`brew`/`pacman`
3. 直接下载：`curl`/`wget` 从官方源下载
4. 内置实现：shell/python 脚本等价逻辑

| 安装方式 | checksec 安装命令 |
|---------|------------------|
| pip | `pip install checksec` |
| uv | `uv tool install checksec` |
| Ubuntu/Debian | `apt-get install -y checksec` |
| CentOS | `yum install -y epel-release && yum install -y checksec` |
| Fedora | `dnf install -y checksec` |
| Arch | `pacman -S checksec` |
| macOS | `brew install checksec` |
| 下载脚本 | `mkdir -p ~/.local/bin && curl -sL https://raw.githubusercontent.com/slimm609/checksec.sh/master/checksec -o ~/.local/bin/checksec && chmod +x ~/.local/bin/checksec` |
| 上游地址 | <https://github.com/slimm609/checksec> |

安装后必须验证：

```bash
which checksec >/dev/null 2>&1 && checksec --help >/dev/null 2>&1
```

#### 安装成功 → 继续

所有缺失工具安装成功且验证通过后，回到 Step 2 重新检查，确保全部就绪。若全部就绪，状态设为 `ready`，进入 Step 7。

#### 安装失败 → 询问用户是否降级

如果自动安装尝试后仍有工具缺失，**不得直接降级**。必须使用 `question` 工具询问用户：

```text
╔══════════════════════════════════════════════════════════════╗
║  ⚠️ 以下工具自动安装失败：                                   ║
║    - {工具名} — 尝试了 pip / 系统包管理器 / 直接下载       ║
║                                                            ║
║  安装失败后，扫描可以以降级模式继续：                        ║
║    · 部分扫描维度将使用备选方案（功能受限）                  ║
║    · 检查精度和覆盖范围可能降低                              ║
║    · 所有降级项会在最终报告中标注                            ║
║                                                            ║
║  请选择：                                                   ║
║    [A] 接受降级 — 以降级模式继续扫描                         ║
║    [B] 拒绝降级 — 终止扫描，我手动安装后再重试               ║
╚══════════════════════════════════════════════════════════════╝
```

- 用户选 [A]：状态设为 `degraded`（用户确认），进入 Step 7。
- 用户选 [B]：状态设为 `blocked`，终止扫描，输出安装指南。

### Step 7: 生成依赖报告

```json
{
  "status": "ready | degraded | blocked",
  "available": ["grep", "find", "file", "stat", "checksec"],
  "installed": [],
  "missing": [],
  "degradations": [
    {
      "tool": "readelf",
      "impact": "ELF 降级检查不可用",
      "fallback": "skip"
    }
  ]
}
```

判定规则：

- `ready`：所有核心和重要依赖可用，进入 Phase 0。
- `degraded`：核心依赖可用，部分重要依赖缺失但有降级方案，**且用户已在 Step 3 或 Step 6 中明确同意降级**。
- `blocked`：核心依赖缺失且无法安装或用户拒绝降级，终止扫描并输出安装指南。

## 降级链

> ⚠️ 降级链中的所有备选方案**仅在用户明确同意降级模式后**才启用。
> 在用户同意之前，任何工具缺失都必须阻断并通知用户。

```text
checksec 不可用:
  -> 尝试自动安装（pip > 系统包管理器 > curl 下载）
  -> 安装失败 -> 询问用户是否接受降级
  -> 用户拒绝 -> BLOCKED 终止
  -> 用户同意 -> 降级到 readelf + objdump 手动解析
  -> readelf 也不可用 -> 降级到 python3 ELF header 解析
  -> python3 也不可用 -> ELF 扫描维度跳过（SKIP）

grep 不可用:
  -> 降级到 python3 正则匹配
  -> python3 也不可用 -> BLOCKED

find 不可用:
  -> 降级到 ls -R + shell glob
  -> 都不可用 -> BLOCKED

file 不可用:
  -> 降级到检查 ELF magic bytes（xxd/head -c4）
  -> xxd 不可用时降级到 od
  -> 降级到按扩展名分类

stat 不可用:
  -> 降级到 ls -la 权限字符串解析
  -> 不可用 -> 权限检查维度跳过（SKIP）
```

## BLOCKED 状态输出格式

```text
安全扫描已阻止 - 缺失依赖

以下必需工具不可用：
  - {tool_name} - {purpose}

安装指南：
  - Fedora:   sudo dnf install -y {package}    # 需 root 权限
  - Ubuntu:   sudo apt install -y {package}   # 需 root 权限
  - CentOS:   sudo yum install -y {package}   # 需 root 权限
  - macOS:    brew install {package}
  - pip:      pip install {package}

请安装缺失工具后重试。

如需自动安装，请以 root 身份（`sudo -i`）重新启动扫描。
```

## 异常处理

| 异常 | 处理 |
|------|------|
| 包管理器权限不足 | 提示用户以管理员权限安装，或使用用户级安装（pip --user） |
| 网络不可用 | 跳过在线安装，询问用户是否接受降级 |
| 安装后验证失败 | 询问用户是否接受降级，而非直接启用降级链 |
| 用户拒绝降级 | 终止扫描，输出 BLOCKED 状态和安装指南 |
| ldd 命令不可用 | 跳过共享库检查；macOS 改用 `otool -L` |
