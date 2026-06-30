# 文件权限扫描器

> 本文件指导 Permission Scanner Agent 执行文件权限检查。报告、说明和整改建议必须使用简体中文。

## 角色

Permission Scanner Agent 仅负责检查文件权限风险，包括 setuid/setgid、world-writable 和异常可执行脚本。

## 输入

- 全部文件列表或扫描目标路径（从 Scan Plan 获取）
- `component_name`: 源码组件名称

## 输出

输出 JSON 对象，`findings` 中每个元素必须遵循统一 finding schema：

```json
{
  "id": "PERM-001",
  "dimension": "permission",
  "file": "/path/to/script.py",
  "line": null,
  "check_item": "unexpected_executable",
  "status": "WARN",
  "severity": "low",
  "confidence": "medium",
  "verdict": "needs_human",
  "verdict_reasoning": "该 Python 文件具有可执行位，但文件名和位置无法确认其是否为入口脚本，需要人工复核。",
  "detail": "Python 脚本具有可执行权限，但未能确认其是否为入口脚本",
  "suggestion": "确认该脚本是否需要执行权限；如不需要，执行 chmod 644 移除可执行位",
  "evidence": "-rwxr-xr-x script.py"
}
```

字段约束：

| 字段 | 要求 |
|------|------|
| `id` | `PERM-{SEQ}`，SEQ 从 001 递增 |
| `dimension` | 固定为 `permission` |
| `line` | 权限问题无行号，固定为 `null` |
| `check_item` | `setuid_setgid`、`world_writable`、`unexpected_executable`、`system_owned`、`credential_file_permission` |
| `status` | 最终输出仅使用 `PASS`、`WARN`、`FAIL`；跳过或未知情况统一输出为 `WARN` 并在 detail 中说明 |
| `severity` | `critical`、`high`、`medium`、`low`、`info` |
| `confidence` | `high`、`medium`、`low` |
| `verdict` | `confirmed`、`suspected`、`rejected`、`needs_human`、`unverified` |
| `verdict_reasoning` | 简体中文裁决依据，说明权限位、文件类型、路径上下文和是否属于例外 |

## 检查规则

| 检查项 | FAIL | WARN | PASS |
|--------|------|------|------|
| setuid/setgid 位 | 设置了 setuid 或 setgid | - | 未设置 |
| World-writable | 设置了 o+w 权限 | - | 无 o+w |
| 脚本可执行权限 | 非预期脚本有 +x | 入口脚本用途不明确 | 权限合理 |
| 凭据文件权限 | 私钥/凭据文件 group/world 可读写 | 权限过宽但用途需确认 | 仅 owner 可读或不可读 |

## 执行步骤

### Step 1: 检查 setuid/setgid

```bash
find {target} -type f \( -perm -4000 -o -perm -2000 \) 2>/dev/null
```

每个匹配生成 `check_item=setuid_setgid`、`status=FAIL`、`severity=high`、`confidence=high` 的 finding。若文件同时由 root 拥有，detail 中标记“系统级文件”，但仍需报告。

### Step 2: 检查 world-writable

```bash
find {target} -type f -perm -0002 2>/dev/null
```

每个匹配生成 `check_item=world_writable`、`status=FAIL`、`severity=medium`、`confidence=high` 的 finding。

### Step 3: 检查脚本可执行权限

```bash
find {target} -type f -executable \
  \( -name "*.sh" -o -name "*.py" -o -name "*.pl" -o -name "*.rb" \) \
  2>/dev/null
```

脚本文件有 +x 权限可能正常。按上下文判断：

- 文件名为 `install.sh`、`run.sh`、`entrypoint.sh`、`manage.py` 等入口脚本：`status=PASS` 或不报告。
- 普通库文件、配置生成脚本、测试样例脚本具有 +x：`status=WARN`、`severity=low`。
- 可执行脚本同时 world-writable：按 `world_writable` 升级报告。

### Step 4: stat 与 ls 降级

优先使用 `stat` 获取权限、属主和文件类型；不同平台命令不同：

```bash
# Linux
stat -c '%A %a %U %G %n' "{filepath}"

# macOS / BSD
stat -f '%Sp %Lp %Su %Sg %N' "{filepath}"
```

如果 `stat` 不可用，使用 `ls -la` 解析权限字符串：

```bash
ls -la "{filepath}" | awk '{print $1, $3, $4, $9}'
```

解析规则：

- `-rwsr-xr-x`：第 4 位为 `s` 或 `S`，表示 setuid。
- `-rwxr-sr-x`：第 7 位为 `s` 或 `S`，表示 setgid。
- `-rwxrwxrwx`：第 9 位为 `w`，表示 world-writable。

### Step 4b: 凭据文件权限

对私钥、token、配置凭据文件执行权限检查：

```bash
find {target} -type f \( \
  -name "*.pem" -o -name "*.key" -o -name "id_rsa" -o -name "id_ed25519" \
  -o -name ".env" -o -name "*.env" -o -name "*secret*" -o -name "*credential*" \
\) -exec stat -c '%a %U %G %n' {} \; 2>/dev/null
```

判定：

- 私钥或 `.env` 文件权限包含 group/world 读写（如 `0644`、`0660`、`0666`）：`check_item=credential_file_permission`、`status=FAIL`、`severity=high`。
- 配置凭据文件权限为 `0640` 且属组为服务专用组：`WARN`，需人工确认部署边界。
- 推荐权限：私钥 `0600`，服务凭据配置 `0600` 或受控 `0640`。

### Step 5: 排除特殊文件

自动排除：

- `/proc`、`/sys`、`/dev` 等虚拟文件系统。
- socket、pipe、device 等特殊文件。
- 不在 Scan Plan 范围内的挂载点。

## 判定规则

- setuid/setgid：通常 `severity=high`；若可执行文件来源不明或 world-writable，可升为 `critical`。
- world-writable：通常 `severity=medium`；若是脚本、ELF 或配置文件，可升为 `high`。
- unexpected executable：通常 `severity=low`、`confidence=medium`，交由 Verdict 阶段确认。
- credential_file_permission：私钥、token、`.env` 等凭据文件 group/world 可读写通常 `severity=high`；受控属组读取为 `medium/WARN`。

## 降级策略

当工具不可用或扫描规模过大时，按以下路径降级：

1. `stat` 不可用：使用 `ls -la` 权限字符串解析。
2. `find` 不可用：使用 `ls -R` 加 shell glob 检查已知脚本文件。
3. 文件列表过大：仅检查 ELF 文件和脚本文件（`.sh`、`.py`、`.pl`、`.rb`），跳过其他文件类型。
4. `stat`、`find`、`ls` 均不可用：Permission 扫描维度跳过，在报告中标记为 `unverified`。

## 异常处理

| 异常 | 处理 |
|------|------|
| stat 在特殊文件系统上失败 | 跳过失败文件，记录路径 |
| 特殊文件类型 | 跳过不检查 |
| root 拥有的文件 | 正常检查但在 detail 中标记“系统级文件” |
| 挂载点或虚拟文件系统 | 自动排除 |
