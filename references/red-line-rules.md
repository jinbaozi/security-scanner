# 红线规则库 (Red-Line Rules)

> Pattern 权威源。可绑定 RL-ID 必须 ⊆ `references/redline-mapping.md` 的 `rl_ids`。
> Scanner 运行时加载维内 `patterns-*.md` + `redline-clauses.md`，**不要**整本注入本文件。
> INFO（RL-300+）仅作推荐提示，不得绑定为 FAIL 条款。

## 规则格式

| 字段 | 说明 |
|------|------|
| `id` | `RL-{NNN}`，须在 mapping 中声明（INFO 除外） |
| `category` | 算法/协议/凭据等类别 |
| `name` | 规则中文名 |
| `severity` | `critical` / `high` / `medium` / `low` / `info` |
| `pattern` | 正则或关键字；无 pattern 的扩展 ID 不得虚构命中 |
| `evidence_required` | 最少证据 |
| `false_positive_pattern` | 误报排除 |
| `remediation` | 修复建议（简体中文） |

## 类别总览

| 类别 | 编号区间 | 主要条款 |
|------|---------|----------|
| 不安全对称算法 | RL-001 ~ RL-008 | 5.1.4 |
| 不安全非对称算法 | RL-020 ~ RL-024 | 5.1.4 |
| 不安全 Hash | RL-040 ~ RL-047 | 5.1.4 / 6.1.1 |
| 伪加密 | RL-060 ~ RL-063 | 5.1.1 |
| 不安全随机数 | RL-080 ~ RL-084 | 5.1.3 / 3.1.3 |
| 不安全协议 | RL-100 ~ RL-119 | 5.1.4 / 6.1.2 / 7.1.3 |
| 库默认不安全能力 | RL-120 ~ RL-125 | 5.1.2（manual） |
| 个人数据 | RL-140 ~ RL-144 | 9.1.1 / 4.3.2 |
| 默认账号 | RL-160 ~ RL-162 | 4.1.1 / 7.1.4 |
| 隐藏后门/未公开接口 | RL-180 ~ RL-182 | 4.1.1 / 4.1.2 |
| 扩展占位（无强制 pattern） | RL-200+ | 见 mapping |

## 规则清单

### 不安全对称算法（条款 5.1.4）

| ID | 名称 | severity | pattern | 修复建议 |
|----|------|---------|---------|---------|
| RL-001 | DES 使用 | high | `\bDES(_|\b)\|des_encrypt\|des_crypt` | 改用 AES-128 或 SM4 |
| RL-002 | 3DES 使用 | high | `\b3DES\|TripleDES\|DES_ede\|des3` | 改用 AES-256-GCM |
| RL-003 | RC4 使用 | high | `\bRC4\|ARCFOUR\|rc4_encrypt` | 改用 AES 或 ChaCha20 |
| RL-004 | Blowfish 使用 | medium | `\bBlowfish\|BF_encrypt\|blowfish` | 改用 AES |
| RL-005 | IDEA 使用 | medium | `\bIDEA\|idea_encrypt` | 改用 AES |
| RL-006 | SKIPJACK 使用 | high | `\bSKIPJACK\|skipjack_encrypt\|skipjack_set_key` | 改用 AES-GCM 或 SM4 |
| RL-007 | RC2 使用 | high | `\bRC2\|rc2_encrypt\|RC2-CBC\|RC2-ECB` | 改用 AES-GCM 或 SM4 |
| RL-008 | AES-ECB 模式 | high | `AES/ECB\|EVP_aes_.*_ecb\|MODE_ECB` | 改用 AES-GCM/CCM 或 SM4-GCM |

### 不安全非对称算法（条款 5.1.4）

| ID | 名称 | severity | pattern | 修复建议 |
|----|------|---------|---------|---------|
| RL-020 | RSA 密钥 < 2048 | high | `RSA_generate_key\([0-9]{1,3}\)\|RSA_generate_key_ex\([a-z_]+,\s*[0-9]{1,3}` | 改用 RSA ≥ 2048 位 |
| RL-021 | DSA 密钥 < 2048 | high | `DSA_generate_key\([0-9]{1,3}\)\|DSA_generate_parameters_ex\([a-z_]+,\s*[0-9]{1,3}` | 改用 DSA ≥ 2048 位或 Ed25519 |
| RL-022 | ElGamal 使用 | high | `ElGamal\|elgamal_encrypt` | 改用 ECIES 或 RSA-OAEP |
| RL-023 | DH 512 位参数 | high | `DH_generate_parameters_ex\([^,]+,\s*512\|dhparam\s+512\|ffdhe512` | 改用 ECDHE 或 DH ≥ 2048 位 |
| RL-024 | DH 1024 位参数 | high | `DH_generate_parameters_ex\([^,]+,\s*1024\|dhparam\s+1024\|ffdhe1024` | 改用 ECDHE 或 DH ≥ 2048 位 |

### 不安全 Hash（条款 5.1.4 / 6.1.1）

| ID | 名称 | severity | pattern | evidence_required | 修复建议 |
|----|------|---------|---------|------------------|---------|
| RL-040 | MD5 密码用途 | high | `md5\([^)]*(?:password\|passwd\|pwd)[^)]*\)` | 调用方变量名包含 password | 改用 bcrypt/scrypt/Argon2 |
| RL-041 | MD5 签名用途 | high | `md5.*sign\|sign.*md5` | 上下文含 sign | 改用 SHA-256 + RSA/ECDSA |
| RL-042 | MD5 证书指纹 | medium | `md5.*(?:cert\|certificate\|fingerprint)` | 上下文含 cert | 改用 SHA-256 |
| RL-043 | SHA-1 签名 | high | `sha1.*sign\|sign.*sha1\|SHA1withRSA\|SHA-1WithRSA` | 上下文含 sign/cert | 改用 SHA-256 + RSA/ECDSA |
| RL-044 | SHA-1 证书 | high | `sha1.*(?:cert\|certificate)\|sha1WithRSAEncryption` | 上下文含 cert | 改用 SHA-256 |
| RL-045 | HMAC 截断 96 位 | medium | `HMAC-?(?:MD5\|SHA1\|SHA256)-?96\|hmac.*truncate.*96` | 上下文含认证/完整性校验 | 改用完整长度 HMAC-SHA-256 |
| RL-046 | MD2 使用 | high | `\bMD2\b\|md2\(` | 任意密码学用途 | 改用 SHA-256/SM3 |
| RL-047 | MD4 使用 | high | `\bMD4\b\|md4\(` | 任意密码学用途 | 改用 SHA-256/SM3 |

### 伪加密（条款 5.1.1）

| ID | 名称 | severity | pattern | 修复建议 |
|----|------|---------|---------|---------|
| RL-060 | Base64 充当密码加密 | critical | `base64_(?:decode\|encode)\([^)]*(?:password\|passwd\|pwd\|secret\|key\|token)[^)]*\)` | 改用 AES-GCM 等真加密 |
| RL-061 | 自写 XOR 循环 | critical | `for\s*\([^)]+\)\s*\{[^}]*\^=\|while[^}]*\^=` | 改用 AES-GCM |
| RL-062 | 字符串反转充当加密 | medium | `reverse\|reversed\|strrev` 紧邻 password/secret/key | 改用 AES-GCM |
| RL-063 | Caesar 移位充当加密 | medium | `chr\(ord\([^)]+\)\s*[+\-]\s*[0-9]+\)` 紧邻 key/secret | 改用 AES-GCM |

### 不安全随机数（条款 5.1.3 / 3.1.3）

| ID | 名称 | severity | pattern | evidence_required | 修复建议 |
|----|------|---------|---------|------------------|---------|
| RL-080 | Math.random 派生 key | critical | `Math\.random\([^)]*\).*(?:key\|iv\|salt\|token\|nonce)` | 上下文含 key/iv/salt/token/nonce | 改用 crypto.getRandomValues |
| RL-081 | java.util.Random 派生 key | critical | `new\s+Random\(\).*(?:nextBytes\|nextInt).*(?:key\|iv\|salt)` | 上下文含 key/iv/salt | 改用 SecureRandom |
| RL-082 | C rand() 派生 key | critical | `rand\(\).*(?:key\|iv\|salt)` | 上下文含 key/iv/salt | 改用 RAND_bytes |
| RL-083 | time() 派生 key | critical | `time\([^)]*\).*(?:key\|iv\|salt\|seed)` | 上下文含 key/iv/salt/seed | 改用 RAND_bytes |
| RL-084 | mt_rand 派生 key | critical | `mt_rand\([^)]*\).*(?:key\|iv\|salt)` | 上下文含 key/iv/salt | 改用 random_bytes 或 random_int |

### 不安全协议（条款 5.1.4 / 6.1.2 / 7.1.3）

| ID | 名称 | severity | pattern | 修复建议 |
|----|------|---------|---------|---------|
| RL-100 | SSLv3 启用 | high | `SSLv3\|SSLv23\|sslv3\|PROTOCOL_SSLv3` | 改用 TLSv1.2 或 TLSv1.3 |
| RL-101 | SSLv2 启用 | high | `SSLv2\|sslv2` | 改用 TLSv1.2 或 TLSv1.3 |
| RL-102 | TLSv1.0 启用 | high | `TLSv1\.0\|TLS1\.0\|PROTOCOL_TLSv1` | 改用 TLSv1.2 或 TLSv1.3 |
| RL-103 | TLSv1.1 启用 | medium | `TLSv1\.1\|TLS1\.1\|PROTOCOL_TLSv1_1` | 改用 TLSv1.2 或 TLSv1.3 |
| RL-104 | Telnet 协议 | high | `telnet\|TELNET\|telnetlib\.` | 改用 SSHv2 |
| RL-105 | HTTP 明文传输敏感字段 | high | `http://[^"]*(?:password\|token\|api_key)` | 改用 HTTPS |
| RL-106 | TFTP 明文文件传输 | high | `\btftp\b\|tftpd\|in\.tftpd\|69/udp` | 改用 SFTP/HTTPS 并启用认证 |
| RL-107 | SNMPv1 | high | `SNMPv1\|snmp-server community\|version\s+1` | 改用 SNMPv3 并启用认证加密 |
| RL-108 | SNMPv2/v2c | high | `SNMPv2c?\|version\s+2c\|community\s+(?:public\|private)` | 改用 SNMPv3 |
| RL-109 | SSHv1.x | high | `SSH-1\.\d\|Protocol\s+1\b\|SSHv1` | 禁用 SSHv1，仅允许 SSHv2 |
| RL-110 | FTP 明文协议 | high | `\bftp://\|vsftpd\|proftpd\|FileZilla Server\|21/tcp` | 改用 SFTP/FTPS |
| RL-111 | FTP 匿名登录 | high | `anonymous_enable\s*=\s*YES\|AllowAnonymous\s+on\|anonymous\s+login` | 禁用匿名登录 |
| RL-112 | Rlogin/Rsh/Rexec | high | `\brlogin\b\|\brsh\b\|\brexec\b\|\.rhosts` | 改用 SSHv2 |
| RL-113 | LDAP 明文 | medium | `ldap://\|389/tcp` | 改用 LDAPS 或 StartTLS |
| RL-114 | SMTP 未配置 STARTTLS | medium | `smtp.*(?:disable.*starttls\|starttls\s*=\s*false)\|25/tcp` | 启用 STARTTLS 或 SMTPS |
| RL-115 | POP3 明文 | medium | `pop3://\|110/tcp` | 改用 POP3S |
| RL-116 | IMAP 明文 | medium | `imap://\|143/tcp` | 改用 IMAPS |
| RL-117 | TLS 3DES Cipher Suite | high | `TLS_.*3DES\|DES-CBC3-SHA\|3DES_EDE_CBC` | 禁用 3DES cipher suite |
| RL-118 | SSH CBC Cipher | medium | `aes(?:128\|192\|256)-cbc\|3des-cbc\|blowfish-cbc` | 改用 aes*-gcm 或 chacha20-poly1305 |
| RL-119 | 明文管理接口 | high | `http://[^"]*(?:admin\|manage\|console\|login)\|management.*http` | 管理面必须启用 HTTPS/SSHv2 |

### 推荐国密算法（INFO，不绑定 FAIL）

| ID | 名称 | severity | pattern | 说明 |
|----|------|---------|---------|------|
| RL-300 | SM4 推荐使用 | info | `\bSM4\|sm4_crypt\|sms4` | 符合场景时可作为对称算法推荐项 |
| RL-301 | SM2 推荐使用 | info | `\bSM2\|sm2_` | 符合场景时可作为非对称算法推荐项 |
| RL-302 | SM3 推荐使用 | info | `\bSM3\|sm3_` | 符合场景时可作为 Hash/摘要推荐项 |

### 库默认不安全能力（条款 5.1.2，manual）

| ID | 库 | 不安全版本 | 触发 capability | 修复建议 |
|----|---|-----------|----------------|---------|
| RL-120 | OpenSSL | < 1.1.0 | 默认启用 SSLv3 | 升级到 OpenSSL ≥ 1.1.1，禁用 SSLv3 |
| RL-121 | Bouncy Castle | < 1.50 | MD5withRSA 默认签名 | 升级到 Bouncy Castle ≥ 1.70 |
| RL-122 | Python cryptography | < 2.0 | 默认开启 SSLv3 | 升级到 cryptography ≥ 3.0 |
| RL-123 | Java JSSE | < 8u291 | TLSv1.0/1.1 默认启用 | 升级 JDK，禁用 TLSv1.0/1.1 |
| RL-124 | Node.js TLS | < 10.0 | 默认支持 TLSv1.0 | 升级 Node.js，配置 secureOptions |
| RL-125 | Go crypto/tls | < 1.17 | 默认 TLS 1.0 | 升级 Go，配置 minVersion |

scanner 仅可 WARN 且 `redline_clause=null`，不得硬判 5.1.2 FAIL。

### 个人数据（条款 9.1.1 / 4.3.2）

| ID | 名称 | severity | pattern | 修复建议 |
|----|------|---------|---------|---------|
| RL-140 | 身份证明文存储 | critical | `(?:id_card\|idcard\|id_number\|identity_card).*(?:=\|:)["'][^"']+["']` 且上下文无 encrypt/hash/mask | 改用加密存储 + 脱敏显示 |
| RL-141 | 手机号明文存储 | high | `(?:phone\|mobile\|tel\|cellphone).*(?:=\|:)["'][^"']+["']` 且上下文无 encrypt/hash/mask | 改用加密存储 + 脱敏显示 |
| RL-142 | 银行卡号明文存储 | critical | `(?:bank_card\|card_number\|credit_card).*(?:=\|:)["'][^"']+["']` 且上下文无 encrypt/hash/mask | 改用 PCI DSS 合规存储 |
| RL-143 | 个人数据明文 HTTP 传输 | high | `http://[^"]*(?:id_card\|phone\|idcard\|mobile)` | 改用 HTTPS |
| RL-144 | 邮箱明文日志 | medium | `logger\.(?:info\|debug\|error)[^)]*(?:email\|mail)` 且无脱敏 | 脱敏后再记录 |

### 默认账号（条款 4.1.1 / 7.1.4）

| ID | 名称 | severity | pattern | 修复建议 |
|----|------|---------|---------|---------|
| RL-160 | 硬编码 admin 默认密码 | high | `["']admin["']\s*[,;:]\s*["'](?:admin\|123456\|password\|admin123)["']` | 强制首次登录修改密码 |
| RL-161 | 硬编码 root 默认密码 | high | `["']root["']\s*[,;:]\s*["'](?:root\|toor\|123456\|password)["']` | 强制首次登录修改密码 |
| RL-162 | 数据库 init 脚本默认账号 | high | `INSERT INTO.*VALUES.*(?:admin\|root).*['"](\w{4,})['"]` | 强制首次登录修改密码 |

### 隐藏后门/未公开接口（条款 4.1.1 / 4.1.2）

| ID | 名称 | severity | 说明 |
|----|------|---------|------|
| RL-180 | 注释中硬编码后门密码 | critical | 由 comment scanner 检测 |
| RL-181 | 注释中未公开 API 端点 | medium | 由 comment scanner 检测 |
| RL-182 | 注释中未公开命令行参数 | medium | 由 comment scanner 检测 |

### 扩展占位（mapping 已声明；无 pattern 时不得虚构命中）

| ID | 名称 | 条款 | 说明 |
|----|------|------|------|
| RL-200 | 高危公开漏洞 | 2.1.1 | dependency 维；依赖外部 CVE 证据 |
| RL-201 | SBOM/修复关联 | 2.1.2 | dependency 维 |
| RL-202 | EOL/EOM 组件 | 12.1.1 | dependency 维 |
| RL-203 | 漏洞 SLA | 12.1.2 | manual |
| RL-210 | SAST 摄取 | 11.1.1 | secure-coding 维 |
| RL-211 | 危险 API | 11.1.2 | secure-coding 维 |
| RL-212 | 安全函数反模式 | 11.1.2 | secure-coding 维 |
| RL-217 | 硬编码工作密钥 | 4.1.1 / 5.2.1 | secret/crypto |
| RL-218 | 日志泄密 | 4.1.1 / 6.1.4 | secret |
| RL-219 | 隐藏调测入口 | 4.1.1 / 4.1.2 | comment |
| RL-220 | 交付物完整性 | 10.1.1 | integrity |
| RL-230 | 内容合规禁词 | 13.1.1 | content-compliance |
| RL-240 | 端口清单 | 1.1.1 | network；必要性人工 |
| RL-241 ~ RL-257 | 人工合规项 | 见 mapping | automation=manual |
| RL-244 | 会话换发信号 | 3.1.3 | crypto partial |
| RL-246 | 调试工具残留 | 4.3.1 | fileleak |
| RL-247 | root 运行 | 4.4.1 | component-info |
| RL-248 | 明文密钥信号 | 5.2.1 / 6.1.1 | secret/crypto |
| RL-250 | 口令文件权限 | 7.1.1 / 7.1.4 | permission/secret |
| RL-260 | 编译加固/ASLR | 11.2.1 | elf；内核 ASLR 人工 |

## 用户自定义规则

新增自定义 RL 前必须先写入 `redline-mapping.md` 的对应 `rl_ids`，再在此补充 pattern。禁止复用已占用的 mapping ID。
