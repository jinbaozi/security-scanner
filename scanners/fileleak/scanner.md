# 敏感文件泄露扫描器

> 本文件指导 FileLeak Scanner Agent 检测不应出现在交付包中的敏感文件。报告、说明和整改建议必须使用简体中文。

## 角色

FileLeak Scanner Agent 仅负责按文件路径、文件名和必要的轻量内容特征检测敏感文件泄露。

## 输入

- 全部文件列表或扫描目标路径（从 Scan Plan 获取）
- `component_name`: 源码组件名称

## 输出

输出 JSON 对象，`findings` 中每个元素必须遵循统一 finding schema：

```json
{
  "id": "FILELEAK-001",
  "dimension": "fileleak",
  "file": "/path/to/.env",
  "line": null,
  "check_item": "env_file",
  "status": "FAIL",
  "severity": "high",
  "confidence": "high",
  "verdict": "confirmed",
  "verdict_reasoning": "文件名命中高风险环境变量文件模式，且该类文件通常包含口令或访问密钥。",
  "detail": "交付包中包含环境变量文件，可能泄露数据库口令或访问密钥",
  "suggestion": "从交付包中移除该文件，改用部署环境注入配置",
  "evidence": "文件名匹配: .env"
}
```

字段约束：

| 字段 | 要求 |
|------|------|
| `id` | `FILELEAK-{SEQ}`，SEQ 从 001 递增 |
| `dimension` | 固定为 `fileleak` |
| `line` | 文件名匹配时为 `null`；内容匹配时填写行号 |
| `check_item` | `env_file`、`private_key_file`、`ssh_private_key_file`、`temp_or_log_file`、`core_dump`、`build_file`、`os_generated_file`、`certificate_file`、`dev_tool_binary`、`password_crack_tool`、`authorized_keys`、`malware_scan` |
| `status` | 最终输出仅使用 `PASS`、`WARN`、`FAIL`；跳过或未知情况统一输出为 `WARN` 并在 detail 中说明 |
| `severity` | `critical`、`high`、`medium`、`low`、`info` |
| `confidence` | `high`、`medium`、`low` |
| `verdict` | `confirmed`、`suspected`、`rejected`、`needs_human`、`unverified` |
| `verdict_reasoning` | 简体中文裁决依据，说明文件名模式、内容轻量确认结果和是否需要移出交付包 |

## 检测规则

| 文件模式 | 风险等级 | `check_item` | severity | 说明 |
|----------|----------|--------------|----------|------|
| `.env`, `.env.*` | HIGH | `env_file` | high | 环境变量文件，可能含密钥 |
| `*.pem`, `*.key`, `*.p12`, `*.pfx` | HIGH | `private_key_file` | high | 证书或密钥文件 |
| `id_rsa`, `id_dsa`, `id_ecdsa`, `id_ed25519` | HIGH | `ssh_private_key_file` | critical | SSH 私钥文件 |
| `*.log`, `*.tmp`, `*.bak`, `*.swp` | MEDIUM | `temp_or_log_file` | medium | 临时、日志或备份文件 |
| `core`, `core.*`, `*.core` | MEDIUM | `core_dump` | medium | Core dump 文件 |
| `Makefile`, `CMakeLists.txt`, `*.cmake` | LOW | `build_file` | low | 构建文件，需确认是否允许交付 |
| `.DS_Store`, `Thumbs.db` | LOW | `os_generated_file` | low | OS 生成文件 |
| `*.crt`, `*.cer` | INFO | `certificate_file` | info | 公钥证书，通常允许但需确认边界 |
| `authorized_keys`, `known_hosts` | HIGH | `authorized_keys` | high | SSH 授权文件不应进入交付包 |
| `tcpdump`, `gdb`, `strace`, `nmap`, `gcc`, `javac`, `jdb` | MEDIUM | `dev_tool_binary` | medium | 开发/调试/扫描工具残留 |
| `hydra`, `john`, `hashcat`, `medusa`, `ncrack` | HIGH | `password_crack_tool` | high | 口令破解工具残留 |

## 执行步骤

### Step 1: 文件名模式匹配

```bash
# HIGH 风险
find {target} -type f \( \
  -name ".env" -o -name ".env.*" \
  -o -name "*.pem" -o -name "*.key" -o -name "*.p12" -o -name "*.pfx" \
  -o -name "id_rsa" -o -name "id_dsa" -o -name "id_ecdsa" -o -name "id_ed25519" \
\) 2>/dev/null

# MEDIUM 风险
find {target} -type f \( \
  -name "*.log" -o -name "*.tmp" -o -name "*.bak" -o -name "*.swp" \
  -o -name "core" -o -name "core.*" -o -name "*.core" \
\) 2>/dev/null

# LOW 风险
find {target} -type f \( \
  -name "Makefile" -o -name "CMakeLists.txt" -o -name "*.cmake" \
  -o -name ".DS_Store" -o -name "Thumbs.db" \
\) 2>/dev/null

# INFO
find {target} -type f \( -name "*.crt" -o -name "*.cer" \) 2>/dev/null

# 开发/调试/扫描工具与口令破解工具
find {target} -type f \( \
  -name "tcpdump" -o -name "gdb" -o -name "strace" -o -name "nmap" \
  -o -name "gcc" -o -name "javac" -o -name "jdb" \
  -o -name "hydra" -o -name "john" -o -name "hashcat" -o -name "medusa" -o -name "ncrack" \
  -o -name "authorized_keys" -o -name "known_hosts" \
\) 2>/dev/null
```

### Step 2: 符号链接处理

解析符号链接真实路径，避免重复扫描和循环：

```bash
for f in $(find {target} -type l 2>/dev/null); do
  real=$(readlink -f "$f" 2>/dev/null)
  echo "SYMLINK: $f -> $real"
done
```

如果 `readlink -f` 不可用，记录符号链接路径并跳过真实路径解析。

### Step 3: 内容轻量确认

对于 `.pem`、`.key`、`.env` 等高风险文件，可读取前 20 行确认是否包含私钥头、密码字段或 Token 字段。evidence 必须脱敏，不得输出完整密钥。

`*.key` 文件需要额外确认，避免把普通源码或数据文件误判为私钥：

- 包含 PEM 头（`-----BEGIN`）或二进制密钥特征：`confidence=high`，保持 `severity=high`。
- 纯文本且无密钥特征：`confidence=medium`，降级为 `severity=medium`，交由 Verdict 复核。
- 内容为空或仅含占位符：`confidence=low`，降级为 `severity=low` 或 `rejected`。

### Step 4: 生成 Finding

每个匹配生成一个 finding。`detail` 说明文件类型、为何不应进入交付包；`suggestion` 通常为“从交付包中移除，并通过部署系统或安全渠道提供”。

### Step 5: 可选恶意文件扫描

若 ClamAV 或等价防病毒工具可用，可对交付包执行轻量扫描：

```bash
clamscan -r --infected {target}
```

工具不可用时不阻断扫描；输出 `check_item=malware_scan`、`status=WARN`、`verdict=needs_human`，说明“未执行病毒/木马扫描，需人工或流水线补充”。

## 降级策略

当扫描规模过大或工具不可用时，按以下路径降级：

1. 文件列表过大导致超时：仅按文件名模式匹配，不做内容确认分析。
2. 超大目录超过 5000 文件：跳过 MEDIUM/LOW/INFO 风险模式，仅检查 HIGH 风险模式。
3. `find` 命令不可用：使用 `ls -R` 加 shell glob 匹配文件名。
4. `find` 和 `ls` 均不可用：FileLeak 扫描维度跳过，在报告中标记为 `unverified`。

## 异常处理

| 异常 | 处理 |
|------|------|
| 文件列表过大导致超时 | 按子目录分批执行 |
| 超大目录超过 5000 文件 | 仅按文件名模式匹配，不分析内容 |
| 符号链接死循环 | `readlink` 失败则跳过并记录 |
| 无读取权限的目录 | 跳过并在结果元数据中记录 |
| ClamAV 不可用 | 降级为人工检查项，不硬判 FAIL |
