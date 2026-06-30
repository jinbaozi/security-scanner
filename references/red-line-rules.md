# 红线规则库 (Red-Line Rules)

> 本文件集中维护所有红线规则，是 crypto-scanner / network-scanner / component-info-scanner 共同的判定依据。
> 用户可在此扩展自定义规则，无需修改 scanner 核心逻辑。

## 规则格式

每条规则包含以下字段：

| 字段 | 说明 |
|------|------|
| `id` | 规则唯一标识，`RL-{NNN}` |
| `category` | 10 类别之一 |
| `name` | 规则中文名 |
| `severity` | `critical` / `high` / `medium` / `low` / `info` |
| `pattern` | 触发该规则的正则或关键字 |
| `evidence_required` | 判定红线违规所需的最少证据（行号 + 上下文） |
| `false_positive_pattern` | 用于排除误报的反向 pattern |
| `remediation` | 修复建议（简体中文） |

## 类别总览

| 类别 | 编号区间 | 红线编号 |
|------|---------|---------|
| 不安全对称算法 | RL-001 ~ RL-019 | 红线 2 |
| 不安全非对称算法 | RL-020 ~ RL-039 | 红线 2 |
| 不安全 Hash | RL-040 ~ RL-059 | 红线 2 |
| 伪加密 | RL-060 ~ RL-079 | 红线 1 |
| 不安全随机数 | RL-080 ~ RL-099 | 红线 3 |
| 不安全协议 | RL-100 ~ RL-119 | 红线 2 |
| 库默认不安全能力 | RL-120 ~ RL-139 | 红线 2 |
| 个人数据违规处理 | RL-140 ~ RL-159 | 红线 5 |
| 默认账号未披露 | RL-160 ~ RL-179 | 红线 5 |
| 隐藏后门/未公开接口 | RL-180 ~ RL-199 | 红线 4 |

## 规则清单

### 不安全对称算法 (红线 2)

| ID | 名称 | severity | pattern | 修复建议 |
|----|------|---------|---------|---------|
| RL-001 | DES 使用 | high | `\bDES(_|\b)\|des_encrypt\|des_crypt` | 改用 AES-128 或 SM4 |
| RL-002 | 3DES 使用 | high | `\b3DES\|TripleDES\|DES_ede\|des3` | 改用 AES-256-GCM |
| RL-003 | RC4 使用 | high | `\bRC4\|ARCFOUR\|rc4_encrypt` | 改用 AES 或 ChaCha20 |
| RL-004 | Blowfish 使用 | medium | `\bBlowfish\|BF_encrypt\|blowfish` | 改用 AES |
| RL-005 | IDEA 使用 | medium | `\bIDEA\|idea_encrypt` | 改用 AES |
| RL-006 | SKIPJACK 使用 | high | `\bSKIPJACK\|skipjack_encrypt\|skipjack_set_key` | redline_clause=5.1.4；改用 AES-GCM 或 SM4 |
| RL-007 | RC2 使用 | high | `\bRC2\|rc2_encrypt\|RC2-CBC\|RC2-ECB` | redline_clause=5.1.4；改用 AES-GCM 或 SM4 |
| RL-008 | AES-ECB 模式 | high | `AES/ECB\|EVP_aes_.*_ecb\|MODE_ECB` | redline_clause=5.1.4；改用 AES-GCM/CCM 或 SM4-GCM |

### 不安全非对称算法 (红线 2)

| ID | 名称 | severity | pattern | 修复建议 |
|----|------|---------|---------|---------|
| RL-020 | RSA 密钥 < 2048 | high | `RSA_generate_key\([0-9]{1,3}\)\|RSA_generate_key_ex\([a-z_]+,\s*[0-9]{1,3}` | 改用 RSA ≥ 2048 位 |
| RL-021 | DSA 密钥 < 2048 | high | `DSA_generate_key\([0-9]{1,3}\)\|DSA_generate_parameters_ex\([a-z_]+,\s*[0-9]{1,3}` | 改用 DSA ≥ 2048 位或 Ed25519 |
| RL-022 | ElGamal 使用 | high | `ElGamal\|elgamal_encrypt` | 改用 ECIES 或 RSA-OAEP |
| RL-023 | DH 512 位参数 | high | `DH_generate_parameters_ex\([^,]+,\s*512\|dhparam\s+512\|ffdhe512` | redline_clause=5.1.4；改用 ECDHE 或 DH ≥ 2048 位 |
| RL-024 | DH 1024 位参数 | high | `DH_generate_parameters_ex\([^,]+,\s*1024\|dhparam\s+1024\|ffdhe1024` | redline_clause=5.1.4；改用 ECDHE 或 DH ≥ 2048 位 |

### 不安全 Hash (红线 2)

| ID | 名称 | severity | pattern | evidence_required | 修复建议 |
|----|------|---------|---------|------------------|---------|
| RL-040 | MD5 密码用途 | high | `md5\([^)]*(?:password\|passwd\|pwd)[^)]*\)` | 调用方变量名包含 password | 改用 bcrypt/scrypt/Argon2 |
| RL-041 | MD5 签名用途 | high | `md5.*sign\|sign.*md5` | 上下文含 sign | 改用 SHA-256 + RSA/ECDSA |
| RL-042 | MD5 证书指纹 | medium | `md5.*(?:cert\|certificate\|fingerprint)` | 上下文含 cert | 改用 SHA-256 |
| RL-043 | SHA-1 签名 | high | `sha1.*sign\|sign.*sha1\|SHA1withRSA\|SHA-1WithRSA` | 上下文含 sign/cert | 改用 SHA-256 + RSA/ECDSA |
| RL-044 | SHA-1 证书 | high | `sha1.*(?:cert\|certificate)\|sha1WithRSAEncryption` | 上下文含 cert | 改用 SHA-256 |
| RL-045 | HMAC 截断 96 位 | medium | `HMAC-?(?:MD5\|SHA1\|SHA256)-?96\|hmac.*truncate.*96` | 上下文含认证/完整性校验 | redline_clause=5.1.4；改用完整长度 HMAC-SHA-256 或经评估的截断长度 |
| RL-046 | MD2 使用 | high | `\bMD2\b\|md2\(` | 任意密码学用途 | redline_clause=5.1.4；改用 SHA-256/SM3 |
| RL-047 | MD4 使用 | high | `\bMD4\b\|md4\(` | 任意密码学用途 | redline_clause=5.1.4；改用 SHA-256/SM3 |

### 伪加密 (红线 1)

| ID | 名称 | severity | pattern | 修复建议 |
|----|------|---------|---------|---------|
| RL-060 | Base64 充当密码加密 | critical | `base64_(?:decode\|encode)\([^)]*(?:password\|passwd\|pwd\|secret\|key\|token)[^)]*\)` | 改用 AES-GCM 等真加密 |
| RL-061 | 自写 XOR 循环 | critical | `for\s*\([^)]+\)\s*\{[^}]*\^=\|while[^}]*\^=` | 改用 AES-GCM |
| RL-062 | 字符串反转充当加密 | medium | `reverse\|reversed\|strrev` 紧邻 password/secret/key | 改用 AES-GCM |
| RL-063 | Caesar 移位充当加密 | medium | `chr\(ord\([^)]+\)\s*[+\-]\s*[0-9]+\)` 紧邻 key/secret | 改用 AES-GCM |

### 不安全随机数 (红线 3)

| ID | 名称 | severity | pattern | evidence_required | 修复建议 |
|----|------|---------|---------|------------------|---------|
| RL-080 | Math.random 派生 key | critical | `Math\.random\([^)]*\).*(?:key\|iv\|salt\|token\|nonce)` | 上下文含 key/iv/salt/token/nonce | 改用 crypto.getRandomValues |
| RL-081 | java.util.Random 派生 key | critical | `new\s+Random\(\).*(?:nextBytes\|nextInt).*(?:key\|iv\|salt)` | 上下文含 key/iv/salt | 改用 SecureRandom |
| RL-082 | C rand() 派生 key | critical | `rand\(\).*(?:key\|iv\|salt)` | 上下文含 key/iv/salt | 改用 RAND_bytes |
| RL-083 | time() 派生 key | critical | `time\([^)]*\).*(?:key\|iv\|salt\|seed)` | 上下文含 key/iv/salt/seed | 改用 RAND_bytes |
| RL-084 | mt_rand 派生 key | critical | `mt_rand\([^)]*\).*(?:key\|iv\|salt)` | 上下文含 key/iv/salt | 改用 random_bytes 或 random_int |

### 不安全协议 (红线 2)

| ID | 名称 | severity | pattern | 修复建议 |
|----|------|---------|---------|---------|
| RL-100 | SSLv3 启用 | high | `SSLv3\|SSLv23\|sslv3\|PROTOCOL_SSLv3` | 改用 TLSv1.2 或 TLSv1.3 |
| RL-101 | SSLv2 启用 | high | `SSLv2\|sslv2` | 改用 TLSv1.2 或 TLSv1.3 |
| RL-102 | TLSv1.0 启用 | high | `TLSv1\.0\|TLS1\.0\|PROTOCOL_TLSv1` | 改用 TLSv1.2 或 TLSv1.3 |
| RL-103 | TLSv1.1 启用 | medium | `TLSv1\.1\|TLS1\.1\|PROTOCOL_TLSv1_1` | 改用 TLSv1.2 或 TLSv1.3 |
| RL-104 | Telnet 协议 | high | `telnet\|TELNET\|telnetlib\.` | 改用 SSHv2 |
| RL-105 | HTTP 明文传输敏感字段 | high | `http://[^"]*(?:password\|token\|api_key)` | 改用 HTTPS |
| RL-106 | TFTP 明文文件传输 | high | `\btftp\b\|tftpd\|in\.tftpd\|69/udp` | redline_clause=6.1.2；改用 SFTP/HTTPS 并启用认证 |
| RL-107 | SNMPv1 | high | `SNMPv1\|snmp-server community\|version\s+1` | redline_clause=6.1.2；改用 SNMPv3 并启用认证加密 |
| RL-108 | SNMPv2/v2c | high | `SNMPv2c?\|version\s+2c\|community\s+(?:public\|private)` | redline_clause=6.1.2；改用 SNMPv3 |
| RL-109 | SSHv1.x | high | `SSH-1\.\d\|Protocol\s+1\b\|SSHv1` | redline_clause=6.1.2；禁用 SSHv1，仅允许 SSHv2 |
| RL-110 | FTP 明文协议 | high | `\bftp://\|vsftpd\|proftpd\|FileZilla Server\|21/tcp` | redline_clause=6.1.2；改用 SFTP/FTPS |
| RL-111 | FTP 匿名登录 | high | `anonymous_enable\s*=\s*YES\|AllowAnonymous\s+on\|anonymous\s+login` | redline_clause=7.1.3；禁用匿名登录 |
| RL-112 | Rlogin/Rsh/Rexec | high | `\brlogin\b\|\brsh\b\|\brexec\b\|\.rhosts` | redline_clause=6.1.2；改用 SSHv2 |
| RL-113 | LDAP 明文 | medium | `ldap://\|389/tcp` | redline_clause=6.1.2；改用 LDAPS 或 StartTLS |
| RL-114 | SMTP 未配置 STARTTLS | medium | `smtp.*(?:disable.*starttls\|starttls\s*=\s*false)\|25/tcp` | redline_clause=6.1.2；启用 STARTTLS 或 SMTPS |
| RL-115 | POP3 明文 | medium | `pop3://\|110/tcp` | redline_clause=6.1.2；改用 POP3S |
| RL-116 | IMAP 明文 | medium | `imap://\|143/tcp` | redline_clause=6.1.2；改用 IMAPS |
| RL-117 | TLS 3DES Cipher Suite | high | `TLS_.*3DES\|DES-CBC3-SHA\|3DES_EDE_CBC` | redline_clause=5.1.4；禁用 3DES cipher suite |
| RL-118 | SSH CBC Cipher | medium | `aes(?:128\|192\|256)-cbc\|3des-cbc\|blowfish-cbc` | redline_clause=5.1.4；改用 aes*-gcm 或 chacha20-poly1305 |
| RL-119 | 明文管理接口 | high | `http://[^"]*(?:admin\|manage\|console\|login)\|management.*http` | redline_clause=1.1.1；管理面必须启用 HTTPS/SSHv2 等安全通道 |

### 推荐国密算法（INFO，不作为 FAIL）

| ID | 名称 | severity | pattern | 说明 |
|----|------|---------|---------|------|
| RL-300 | SM4 推荐使用 | info | `\bSM4\|sm4_crypt\|sms4` | redline_clause=5.1.4；符合场景时可作为对称算法推荐项 |
| RL-301 | SM2 推荐使用 | info | `\bSM2\|sm2_` | redline_clause=5.1.4；符合场景时可作为非对称算法推荐项 |
| RL-302 | SM3 推荐使用 | info | `\bSM3\|sm3_` | redline_clause=5.1.4；符合场景时可作为 Hash/摘要推荐项 |

### 库默认不安全能力 (红线 2)

| ID | 库 | 不安全版本 | 触发 capability | 修复建议 |
|----|---|-----------|----------------|---------|
| RL-120 | OpenSSL | < 1.1.0 | 默认启用 SSLv3 | 升级到 OpenSSL ≥ 1.1.1，禁用 SSLv3 |
| RL-121 | Bouncy Castle | < 1.50 | MD5withRSA 默认签名 | 升级到 Bouncy Castle ≥ 1.70，禁用 MD5withRSA |
| RL-122 | Python cryptography | < 2.0 | 默认开启 SSLv3 | 升级到 cryptography ≥ 3.0，强制 minimum TLS version |
| RL-123 | Java JSSE | < 8u291 | TLSv1.0/1.1 默认启用 | 升级 JDK，禁用 TLSv1.0/1.1 |
| RL-124 | Node.js TLS | < 10.0 | 默认支持 TLSv1.0 | 升级 Node.js，配置 secureOptions |
| RL-125 | Go crypto/tls | < 1.17 | 默认 TLS 1.0 | 升级 Go，配置 minVersion |

### 个人数据违规处理 (红线 5)

| ID | 名称 | severity | pattern | 修复建议 |
|----|------|---------|---------|---------|
| RL-140 | 身份证明文存储 | critical | `(?:id_card\|idcard\|id_number\|identity_card).*(?:=\|:)["'][^"']+["']` 且上下文无 encrypt/hash/mask | 改用加密存储 + 脱敏显示 |
| RL-141 | 手机号明文存储 | high | `(?:phone\|mobile\|tel\|cellphone).*(?:=\|:)["'][^"']+["']` 且上下文无 encrypt/hash/mask | 改用加密存储 + 脱敏显示 |
| RL-142 | 银行卡号明文存储 | critical | `(?:bank_card\|card_number\|credit_card).*(?:=\|:)["'][^"']+["']` 且上下文无 encrypt/hash/mask | 改用 PCI DSS 合规存储 |
| RL-143 | 个人数据明文 HTTP 传输 | high | `http://[^"]*(?:id_card\|phone\|idcard\|mobile)` | 改用 HTTPS |
| RL-144 | 邮箱明文日志 | medium | `logger\.(?:info\|debug\|error)[^)]*(?:email\|mail)` 且无脱敏 | 脱敏后再记录 |

### 默认账号未披露 (红线 5)

| ID | 名称 | severity | pattern | 修复建议 |
|----|------|---------|---------|---------|
| RL-160 | 硬编码 admin 默认密码 | high | `["']admin["']\s*[,;:]\s*["'](?:admin\|123456\|password\|admin123)["']` | 强制首次登录修改密码 |
| RL-161 | 硬编码 root 默认密码 | high | `["']root["']\s*[,;:]\s*["'](?:root\|toor\|123456\|password)["']` | 强制首次登录修改密码 |
| RL-162 | 数据库 init 脚本默认账号 | high | `INSERT INTO.*VALUES.*(?:admin\|root).*['"](\w{4,})['"]` | 强制首次登录修改密码 |

### 隐藏后门/未公开接口 (红线 4)

| ID | 名称 | severity | 说明 |
|----|------|---------|------|
| RL-180 | 注释中硬编码后门密码 | critical | 由 comment-scanner 检测 |
| RL-181 | 注释中未公开 API 端点 | medium | 由 comment-scanner 检测 |
| RL-182 | 注释中未公开命令行参数 | medium | 由 comment-scanner 检测 |

## 用户自定义规则

在下方添加项目特定的红线规则：

<!-- 示例:
| RL-200 | 内部后门端口 | critical | `:9999.*bind\|listen` | 联系安全团队审查
-->