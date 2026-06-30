# 网络协议与端口 Patterns 库

> 本文件集中维护通信协议和监听端口的 pattern 集合。network-scanner 引用此文件。

## 1. 通信协议 Pattern

### 1.1 安全协议（不告警）

| 协议 | Pattern | 备注 |
|------|---------|------|
| TLSv1.2 | `TLSv1\.2\|TLS1\.2\|PROTOCOL_TLSv1_2` | 推荐 |
| TLSv1.3 | `TLSv1\.3\|TLS1\.3\|PROTOCOL_TLSv1_3` | 推荐 |
| SSHv2 | `SSH-2\.0\|ssh\.ServerConfig\|paramiko` | 推荐 |
| HTTPS | `https://` | 推荐 |
| WSS | `wss://` | 推荐 |
| gRPC over TLS | `grpc\.tls` | 推荐 |

### 1.2 不安全协议（红线 2）

| 协议 | Pattern | severity |
|------|---------|---------|
| SSLv3 | `SSLv3\|PROTOCOL_SSLv3\|sslv3` | high |
| SSLv2 | `SSLv2\|PROTOCOL_SSLv2\|sslv2` | high |
| TLSv1.0 | `TLSv1\.0\|PROTOCOL_TLSv1(?!\.)\|TLS1\.0` | high |
| TLSv1.1 | `TLSv1\.1\|PROTOCOL_TLSv1_1\|TLS1\.1` | medium |
| Telnet | `telnet\|TELNET\|telnetlib\.\|libtelnet` | high |
| HTTP 明文 | `http://` (无 s) | low (单独)，传输敏感字段时 high |
| TFTP | `\btftp\b\|tftpd\|in\.tftpd\|69/udp` | high |
| SNMPv1 | `SNMPv1\|snmp-server community\|version\s+1` | high |
| SNMPv2/v2c | `SNMPv2c?\|version\s+2c\|community\s+(?:public\|private)` | high |
| SSHv1.x | `SSH-1\.\d\|Protocol\s+1\b\|SSHv1` | high |
| FTP 明文 | `\bftp://\|vsftpd\|proftpd\|FileZilla Server\|21/tcp` | high |
| FTP 匿名登录 | `anonymous_enable\s*=\s*YES\|AllowAnonymous\s+on\|anonymous\s+login` | high |
| Rlogin/Rsh/Rexec | `\brlogin\b\|\brsh\b\|\brexec\b\|\.rhosts` | high |
| LDAP 明文 | `ldap://\|389/tcp` | medium |
| SMTP 未配置 STARTTLS | `smtp.*(?:disable.*starttls\|starttls\s*=\s*false)\|25/tcp` | medium |
| POP3 明文 | `pop3://\|110/tcp` | medium |
| IMAP 明文 | `imap://\|143/tcp` | medium |
| TLS 3DES Cipher Suite | `TLS_.*3DES\|DES-CBC3-SHA\|3DES_EDE_CBC` | high |
| SSH CBC Cipher | `aes(?:128\|192\|256)-cbc\|3des-cbc\|blowfish-cbc` | medium |
| 明文管理接口 | `http://[^"]*(?:admin\|manage\|console\|login)\|management.*http` | high |

## 2. 端口识别 Pattern

### 2.1 代码中的端口

| 语言 | Pattern | 示例 |
|------|---------|------|
| C/C++ | `bind\([^,]+,\s*[^,]+,\s*sizeof\([^)]+\)\s*\)` | `bind(sock, &addr, sizeof(addr))` 后跟端口常量 |
| C/C++ | `htons\([0-9]+\)` | `htons(443)` |
| Go | `net\.Listen\([^,]+,\s*":[0-9]+"\)` | `net.Listen("tcp", ":443")` |
| Go | `\.\.\.\.ListenAndServe\("[^:]*:[0-9]+"\)` | `http.ListenAndServe(":8080", nil)` |
| Python | `socket\.bind\(\(['"][^'"]*['"],\s*[0-9]+\)\)` | `socket.bind(('0.0.0.0', 443))` |
| Python | `app\.run\(.*port\s*=\s*[0-9]+\)` | `app.run(port=8080)` |
| Python | `uvicorn\.run\(.*port\s*=\s*[0-9]+\)` | `uvicorn.run(app, port=8000)` |
| Java | `new\s+ServerSocket\([0-9]+\)` | `new ServerSocket(8443)` |
| Java | `server\.port\s*=\s*[0-9]+` | 配置 |
| JavaScript | `app\.listen\([0-9]+\)` | `app.listen(3000)` |
| JavaScript | `server\.listen\([0-9]+\)` | `server.listen(80)` |
| Rust | `TcpListener::bind\("[^:]*:[0-9]+"\)` | `TcpListener::bind("0.0.0.0:8080")` |
| C# | `TcpListener\([0-9]+\)` | `new TcpListener(8080)` |
| PHP | `socket_create\|socket_bind\|listen\([0-9]+\)` | `socket_listen($sock, 5)` |

### 2.2 配置文件中的端口

| 格式 | Pattern |
|------|---------|
| YAML | `^\s*(?:port\|listen)\s*:\s*[0-9]+` |
| JSON | `"port"\s*:\s*[0-9]+` |
| Properties | `^\s*(?:port\|server\.port)\s*=\s*[0-9]+` |
| TOML | `^\s*port\s*=\s*[0-9]+` |
| .env | `^\s*PORT\s*=\s*[0-9]+` |
| nginx | `listen\s+[0-9]+` |
| Apache | `Listen\s+[0-9]+` |

### 2.3 文档中的端口（用于交叉验证）

| 格式 | Pattern |
|------|---------|
| Markdown | `(?<!\d)(?:port|Port|PORT)[:\s]+[0-9]+` |
| 通用 | `(?<!\d):[0-9]{2,5}(?![\d.])` 在 docs/、README.md、*.md 中 |

## 3. 协议-端口交叉验证

发现端口后，验证：
- 443 → 应配 TLS 协议
- 80 → 应配 HTTP/HTTPS 重定向
- 22 → 应配 SSHv2
- 21 → FTP（应替换为 SFTP）
- 23 → Telnet（红线）
- 25 → SMTP（应配 STARTTLS）
- 389 → LDAP（应配 LDAPS）
- 69/udp → TFTP（红线，应替换为 SFTP/HTTPS）
- 110 → POP3（应替换为 POP3S）
- 143 → IMAP（应替换为 IMAPS）
- 161/udp → SNMP（应使用 SNMPv3）

## 4. 端口号与组件用途对照

| 端口 | 常见用途 | 风险等级 |
|------|---------|---------|
| 80 | HTTP | low（应重定向到 443） |
| 443 | HTTPS | low |
| 22 | SSH | low（应禁用 root 登录） |
| 21 | FTP | high（应替换为 SFTP/FTPS） |
| 23 | Telnet | critical（红线） |
| 69/udp | TFTP | high（红线，应替换为 SFTP/HTTPS） |
| 25 | SMTP | medium（应配 STARTTLS） |
| 110 | POP3 | medium（应替换为 POP3S） |
| 143 | IMAP | medium（应替换为 IMAPS） |
| 161/udp | SNMP | high（应使用 SNMPv3） |
| 3306 | MySQL | high（应限制访问） |
| 5432 | PostgreSQL | high（应限制访问） |
| 6379 | Redis | high（应设密码） |
| 27017 | MongoDB | high（应设认证） |
| 1-1023 | 特权端口 | medium（需要 root 或 capability） |
