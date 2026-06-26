# Phase -1: 环境预检（Pre-flight Check）

> 本文件指导 Orchestrator 执行环境预检，检测和安装所需依赖。

## 执行时机

在 Phase 0（Reconnaissance）之前执行。由 Orchestrator 自身执行，无需派发 subagent。

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
    echo "MISSING: $tool (重要依赖，将尝试安装或降级)"
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
```

### Step 3: 检查二进制依赖的运行依赖

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

### Step 4: 安装缺失依赖

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
| 下载脚本 | `curl -sL https://raw.githubusercontent.com/slimm609/checksec.sh/master/checksec -o /usr/local/bin/checksec && chmod +x /usr/local/bin/checksec` |

安装后必须验证：

```bash
which checksec >/dev/null 2>&1 && checksec --help >/dev/null 2>&1
```

### Step 5: 生成依赖报告

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
- `degraded`：核心依赖可用，部分重要依赖缺失但有降级方案。
- `blocked`：核心依赖缺失且无法安装，终止扫描并输出安装指南。

## 降级链

```text
checksec 不可用:
  -> 尝试自动安装（pip > 系统包管理器 > curl 下载）
  -> 安装失败 -> 降级到 readelf + objdump 手动解析
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
  - pip:      pip install {package}
  - macOS:    brew install {package}
  - Ubuntu:   apt install {package}
  - CentOS:   yum install {package}

请安装缺失工具后重试。
```

## 异常处理

| 异常 | 处理 |
|------|------|
| 包管理器权限不足 | 提示用户以管理员权限安装，或使用用户级安装（pip --user） |
| 网络不可用 | 跳过在线安装，尝试降级方案 |
| 安装后验证失败 | 标记该工具为不可用，启用降级链 |
| ldd 命令不可用 | 跳过共享库检查；macOS 改用 `otool -L` |
