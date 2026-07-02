# 网络协议扫描器

> 本文件指导 Network Scanner Agent 执行网络通信相关检测，包括不安全协议（SSLv3/SSLv2/TLSv1.0/TLSv1.1/Telnet/HTTP 明文）、监听端口识别、端口-协议交叉验证、以及特权端口使用情况。报告、说明和整改建议必须使用简体中文。

## 角色

Network Scanner Agent 仅负责检测源码、配置文件和依赖声明中的通信协议与监听端口问题，不负责密码学算法、硬编码凭证、公网地址、ELF、注释或权限问题。

## 输入

- `source_shards`: 源码文件分片列表
- `config_files`: 配置文件列表
- `dependency_findings`（可选）：Dependency Scanner 输出的 SBOM、漏洞和 `MISSING_LOCK_FILE` 结论，仅作为库版本增强上下文
- `component_name`: 源码组件名称
- `communication_matrix_path`（可选）：用户提供的通信矩阵/端口声明文件；不存在或格式错误时输出 WARN，不阻断扫描
- `references/patterns-network.md`: 网络协议与端口 pattern 库
- `../../references/red-line-rules.md`: 红线规则库
- `../../references/library-vuln-caps.md`: 库版本与默认不安全能力知识库
- `../../references/allowlists.md`: 白名单与例外规则
- `references/redline-clauses.md`: network 维度 redline 条款切片；clause 级映射以本地切片为准，`../../references/red-line-rules.md` 仅作 pattern 库。

## 输出

输出 JSON 对象，包含 `findings` 与 `artifacts`。`findings` 中每个元素必须遵循统一 finding schema：

```json
{
  "id": "NETWORK-001",
  "dimension": "network",
  "file": "/path/to/file.go",
  "line": 9,
  "check_item": "legacy_protocol",
  "status": "FAIL",
  "severity": "high",
  "confidence": "high",
  "verdict": "confirmed",
  "verdict_reasoning": "MinVersion = VersionSSL30，启用 SSLv3，命中红线 RL-100",
  "detail": "服务器配置启用了 SSLv3 协议",
  "suggestion": "改用 TLSv1.2 或 TLSv1.3",
  "evidence": "tls.Config{MinVersion: tls.VersionSSL30}",
  "redline_clause": "5.1.4",
  "rl_ids": ["RL-100"]
}
```

`artifacts.port_inventory` 用于记录监听端口清单：

```json
{
  "artifacts": {
    "port_inventory": [
      {
        "port": 8080,
        "protocol": "tcp",
        "source": "/path/to/server.go:10",
        "evidence": "Addr: \":8080\"",
        "declared_in_communication_matrix": false
      }
    ]
  }
}
```

字段约束：

| 字段 | 要求 |
|------|------|
| `id` | `NETWORK-{SEQ}`，SEQ 从 001 递增 |
| `dimension` | 固定为 `network` |
| `line` | 匹配所在行；无法定位时为 `null` |
| `check_item` | `legacy_protocol`、`port_listening`、`port_privileged`、`port_protocol_mismatch`、`insecure_service` |
| `status` | 最终输出仅使用 `PASS`、`WARN`、`FAIL`；跳过或未知情况统一输出为 `WARN` 并在 detail 中说明 |
| `severity` | `critical`、`high`、`medium`、`low`、`info` |
| `confidence` | `high`、`medium`、`low` |
| `verdict` | 高置信真实问题为 `confirmed`，不确定项为 `needs_human` 或 `unverified`，误报为 `rejected` |
| `verdict_reasoning` | 简体中文裁决依据，说明协议类型、端口、上下文用途、白名单命中情况和是否命中红线 |
| `redline_clause` | 命中 redline 条款编号；无法映射时为 `null` |
| `rl_ids` | 命中的 RL-ID 数组；无映射时为 `[]` |

Redline 追溯约束：WARN/FAIL finding 必须优先从本维度 `references/redline-clauses.md` 选择 `redline_clause` 与 `rl_ids`；不得输出本维度切片或全局 `../../references/redline-mapping.md` 不存在的组合。`RL-120` ~ `RL-125` 对应的 5.1.2 是 manual 证明项，只能作为 `WARN` + `needs_human` 辅助证据输出，`redline_clause=null`、`rl_ids=[]`，不得自动确认为 `FAIL`。

## 执行步骤

### Step 1: 加载参考文件

读取以下参考文件以加载检测规则：

- `references/patterns-network.md`：网络协议与端口 pattern 库（不安全协议、端口识别、协议-端口交叉验证、端口-用途对照）
- `../../references/red-line-rules.md`：红线规则库（RL-100 ~ RL-119 不安全协议、RL-120 ~ RL-139 库默认不安全能力）
- `../../references/library-vuln-caps.md`：库版本与默认不安全能力知识库
- `../../references/allowlists.md`：白名单与例外规则
- `references/redline-clauses.md`：network 维度 redline 条款切片，优先用于 clause 映射。

### Step 2: Layer 1 - 不安全协议检测

按语言执行不安全协议扫描，命中 `references/patterns-network.md` 第 1.2 节 pattern：

```bash
# SSLv3 / SSLv2
grep -rnE "SSLv3|PROTOCOL_SSLv3|sslv3|SSLv2|PROTOCOL_SSLv2|sslv2" {all_files}
grep -rnE "VersionSSL30|VersionSSL20" {go_files}

# TLSv1.0 / TLSv1.1
grep -rnE "TLSv1\.0|TLS1\.0|PROTOCOL_TLSv1(?!\.)" {all_files}
grep -rnE "TLSv1\.1|TLS1\.1|PROTOCOL_TLSv1_1" {all_files}
grep -rnE "VersionTLS10|VersionTLS11" {go_files}

# Telnet
grep -rnE "telnet|TELNET|telnetlib\.|libtelnet" {all_files}

# TFTP / SNMP / SSHv1 / FTP 明文
grep -rnE "\btftp\b|tftpd|in\.tftpd|69/udp" {all_files}
grep -rnE "SNMPv1|SNMPv2c?|snmp-server community|community\s+(public|private)" {all_files}
grep -rnE "SSH-1\.[0-9]|Protocol\s+1\b|SSHv1" {all_files}
grep -rnE "\bftp://|vsftpd|proftpd|anonymous_enable\s*=\s*YES|AllowAnonymous\s+on" {all_files}

# 明文管理接口与不安全 cipher suite
grep -rnE "http://[^\"]*(admin|manage|console|login)|management.*http" {all_files}
grep -rnE "TLS_.*3DES|DES-CBC3-SHA|3DES_EDE_CBC|aes(128|192|256)-cbc|3des-cbc|blowfish-cbc" {all_files}

# HTTP 明文（含敏感字段）
grep -rnE "http://" {all_files}
grep -rnE "http://[^\"]*(password|token|api_key)" {all_files}
```

命中 `legacy_protocol` 规则后，先从本维度 `references/redline-clauses.md` 选择对应 clause，再写入 `redline_clause` 与 `rl_ids`。

### Step 3: Layer 2 - 监听端口识别

按语言执行监听端口 pattern 匹配（`references/patterns-network.md` 第 2.1 节）：

```bash
# C/C++
grep -rnE "bind\([^,]+,\s*[^,]+,\s*sizeof\([^)]+\)\s*\)" {c_cpp_files}
grep -rnE "htons\([0-9]+\)" {c_cpp_files}

# Go
grep -rnE "net\.Listen\([^,]+,\s*\":\"[0-9]+\"\)" {go_files}
grep -rnE "ListenAndServe\(\"[^\"]*:[0-9]+\"\)" {go_files}
grep -rnE 'Addr:[[:space:]]*":[0-9]+"' {go_files}

# Python
grep -rnE "socket\.bind\(\(['\"][^'\"]*['\"],\s*[0-9]+\)\)" {py_files}
grep -rnE "app\.run\(.*port\s*=\s*[0-9]+\)" {py_files}
grep -rnE "uvicorn\.run\(.*port\s*=\s*[0-9]+\)" {py_files}

# Java
grep -rnE "new\s+ServerSocket\([0-9]+\)" {java_files}
grep -rnE "server\.port\s*=\s*[0-9]+" {java_files}

# JavaScript
grep -rnE "app\.listen\([0-9]+\)" {js_files}
grep -rnE "server\.listen\([0-9]+\)" {js_files}

# Rust / C# / PHP
grep -rnE "TcpListener::bind\(\"[^\"]*:[0-9]+\"\)" {rust_files}
grep -rnE "TcpListener\([0-9]+\)" {cs_files}
grep -rnE "listen\([0-9]+\)|socket_create|socket_bind" {php_files}
```

### Step 4: Layer 3 - 配置文件端口识别

执行配置文件端口识别（`references/patterns-network.md` 第 2.2 节）：

```bash
grep -rnE "^\s*(?:port|listen)\s*:\s*[0-9]+" {yaml_files}
grep -rnE "\"port\"\s*:\s*[0-9]+" {json_files}
grep -rnE "^\s*(?:port|server\.port)\s*=\s*[0-9]+" {properties_files}
grep -rnE "^\s*port\s*=\s*[0-9]+" {toml_files}
grep -rnE "^\s*PORT\s*=\s*[0-9]+" {env_files}
grep -rnE "listen\s+[0-9]+" {nginx_files}
grep -rnE "Listen\s+[0-9]+" {apache_files}
```

对每个识别到的端口输出 finding，`check_item=port_listening`，`severity=info`，`status=PASS`（仅做信息记录，不视为问题），并同步写入 `artifacts.port_inventory`。端口清单至少包含端口号、协议（未知时填 `unknown`）、来源位置和 evidence。

### Step 5: Layer 4 - 端口-协议交叉验证

将 Layer 3/4 命中的端口与 `references/patterns-network.md` 第 3 节交叉验证：

- 443 → 应配 TLS 协议
- 80 → 应配 HTTP/HTTPS 重定向
- 22 → 应配 SSHv2
- 21 → FTP（应替换为 SFTP/FTPS）
- 23 → Telnet（红线）
- 25 → SMTP（应配 STARTTLS）
- 389 → LDAP（应配 LDAPS）
- 69/udp → TFTP（红线，应替换为 SFTP/HTTPS）
- 110 → POP3（应替换为 POP3S）
- 143 → IMAP（应替换为 IMAPS）
- 161/udp → SNMP（应使用 SNMPv3）

未匹配上预期协议时，输出 `check_item=port_protocol_mismatch`、`severity=medium/warn` 的 finding。

### Step 6: Layer 5 - 特权端口与高危服务识别

按 `references/patterns-network.md` 第 4 节判定风险等级：

```bash
# 特权端口（1-1023）需要 root 或 capability
grep -rnE "[\"':(]\s*(?:[1-9]|[1-9][0-9]|[1-9][0-9][0-9])\s*[\")]" {all_files} | head -n 5
```

对每个特权端口或高危服务（21/23/69/110/143/161/3306/5432/6379/27017 等）输出 `check_item=port_privileged` 或 `insecure_service`、`severity=high/critical`、`status=FAIL` 的 finding，并按本地切片关联对应红线（23 → 7.1.3/RL-104，69 → 7.1.3/RL-106，161 → 7.1.3/RL-107/RL-108，21 → 7.1.3/RL-110）。

### Step 7: 通信矩阵对账（可选）

若提供 `communication_matrix_path`，读取其中声明的端口、协议、方向和用途，与 `artifacts.port_inventory` 对账：

- 端口清单存在但通信矩阵未声明：输出 `check_item=port_protocol_mismatch`、`status=WARN`、`verdict=needs_human`。
- 通信矩阵声明但扫描未发现：写入 audit_log，不直接输出 FAIL。
- `communication_matrix_path` 不存在、无法读取或格式错误：输出 `WARN` finding，说明“缺少通信矩阵，仅输出 port_inventory”，不阻断扫描。

### Step 8: 库版本知识库匹配

读取 `../../references/library-vuln-caps.md`，匹配项目依赖文件中的库版本是否在 insecure_versions 范围。命中 `RL-120` ~ `RL-125` 时，`check_item=library_vuln`，`severity=high`，`status=WARN`，`verdict=needs_human`，`redline_clause=null`，`rl_ids=[]`。

若 Dependency Scanner 已提供 SBOM 或漏洞 finding，优先消费其 `artifacts.sbom` 与 `known_vulnerability` 结论补充 evidence。Network Scanner 不产出 `MISSING_LOCK_FILE`；缺少 lock 文件由 Dependency Scanner 主责报告。

### Step 9: Finding 输出

将所有 Layer 1-8 命中、且未在白名单中排除的问题，转换为统一 finding schema 输出。

每个 finding 的 id 从 `NETWORK-001` 开始递增，dimension 固定为 `network`。

## 判定规则

### status

- `FAIL`：确认命中本维度 `references/redline-clauses.md` 中的自动化或部分自动化条款，且未在白名单中。
- `WARN`：可能命中红线但需要人工确认（如端口-协议不匹配但用途不明），或命中库版本知识库但需升级；命中 `RL-120` ~ `RL-125` 时必须为 `WARN` + `needs_human`。
- `PASS`：仅做信息记录（如 `check_item=port_listening` 的纯端口识别，不视为问题）。

### confidence

- `high`：明确命中红线 pattern，且上下文确认为非安全用途。
- `medium`：可疑命中但用途不明（需要人工判断）。
- `low`：仅关键字命中但 pattern 不完整（如裸字符串 "telnet" 出现在注释或文档中）。

### severity

| check_item | severity 默认值 | 说明 |
|------------|----------------|------|
| `legacy_protocol` | high（SSLv3/SSLv2/TLSv1.0） / medium（TLSv1.1） / high（Telnet） | 不安全通信协议 |
| `port_listening` | info | 端口识别（仅信息记录） |
| `port_privileged` | medium | 特权端口（1-1023）使用 |
| `port_protocol_mismatch` | medium | 端口与协议不匹配 |
| `insecure_service` | high（21/69/110/143/161）/ critical（23 Telnet） | 高危服务（FTP/Telnet/TFTP/SNMP/数据库默认端口） |
| `library_vuln` | high | 库版本命中 insecure_versions |

### verdict

- `confirmed`：高置信真实问题，命中红线且上下文确认。
- `suspected`：可能命中红线但需要更多上下文。
- `needs_human`：需要人工审查（如端口-协议用途模糊）。
- `rejected`：误报（如测试样例、注释说明、白名单内）。
- `unverified`：无法自动验证。

## 异常处理

| 异常 | 处理 |
|------|------|
| 关键字匹配超过 1000 条 | 提高 Layer 1 过滤阈值，仅保留有明确 API 调用的匹配 |
| 大型二进制文件误匹配 | 通过 `file` 命令排除非文本文件 |
| UTF-16 等编码文件 | 尝试 `iconv` 转换；失败则跳过并记录 |
| 库版本无法解析 | 输出 `WARN` 并在 detail 中说明版本解析失败 |
| 端口字符串带前缀（如 "tcp/8080"） | 提取数字部分后做交叉验证 |
| 监听地址为 Unix Socket | 跳过端口检查，仅记录监听事实 |
| 协议-端口用途模糊（如 8080 同时被 HTTP/HTTPS 使用） | 输出 `needs_human` 并在 verdict_reasoning 中说明 |
| `communication_matrix_path` 缺失或格式错误 | 输出 WARN，不阻断扫描；报告中标注仅生成 `port_inventory` |
| 白名单命中 | 标记 `rejected` 并在 verdict_reasoning 中说明白名单规则 |
