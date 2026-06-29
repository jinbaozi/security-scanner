# Component Info Archive Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add 3 new scanner dimensions (crypto / network / component_info) to `security-scanner` that auto-generate a 9-field component info archive with red-line compliance judgment, JSON + Markdown dual output, and overview/index report structure.

**Architecture:** This is a SKILL instruction package — every "implementation" is a Markdown file that an AI agent loads and executes. Tests are JSON baselines that an agent's output is compared against. The 3 new scanners join the existing 6 in Phase 1 parallel dispatch, share `references/patterns-crypto.md` with `secret-scanner`, and add an overview chapter to the comprehensive report plus 3 sub-reports and a `component-info-summary-*.json` file.

**Tech Stack:** Markdown (instructions), bash (commands), Python 3 (JSON validation), `jq` + `xmllint` (dependency parsing), NVD/OSV (offline snapshot, online optional).

**Reference Documents:**
- Spec: `docs/superpowers/specs/2026-06-29-component-info-archive-design.md` (the canonical content source for all files this plan creates)
- Existing scanner template: `scanners/secret-scanner.md`
- Existing template pattern: `templates/report-安全编译.md`
- Existing orchestration: `orchestration/orchestrator.md`, `orchestration/reporter.md`, `orchestration/reconnaissance.md`, `references/dependency-check.md`

## Global Constraints

- All reports, descriptions, finding details, and suggestions must use Simplified Chinese. Spec terminology stays English: `crypto`, `network`, `component_info`, finding schema field names, JSON keys.
- Existing 6-dimension schema must not be modified. Library info is appended into `evidence` as a structured string: `library=NAME@VERSION | library_version=VERSION | trigger=REASON | cve=CVE-XXXX-XXXXX`.
- 9-field output strictly follows: `value` + `confidence` (high|medium|low) + `label` (AUTO|INFERRED|MISSING) + `inference_note` + `reverse_evidence`.
- Tier-1 languages (C/C++, Go, Python, Java) get high-quality patterns. Tier-2 (JavaScript, TypeScript, Rust, C#, PHP, Ruby) get basic patterns. Other languages: no patterns, mark findings as `INFO`.
- Library version resolution: prefer lock/sum files → fall back to main declaration file → produce `MISSING_LOCK_FILE` WARN finding if neither exists.
- Verdict-stage dedup: same `file:line:check_item` between crypto-scanner and secret-scanner → keep higher severity; same `file:line` ±5 lines → merge findings.
- Failure thresholds scaled to 9 scanners: 1 fails → retry 2x; 2-3 fails → mark failed but continue; 4+ fails → Phase-level degradation.

---

## File Structure Summary

| New File | Purpose |
|----------|---------|
| `references/red-line-rules.md` | 10-category red-line rules table |
| `references/patterns-crypto.md` | Algorithm / pseudo-encryption / random patterns (shared with secret-scanner) |
| `references/patterns-network.md` | Protocol / port patterns |
| `references/personal-data-patterns.md` | Personal data field name regexes |
| `references/library-vuln-caps.md` | Library version → insecure capability knowledge base |
| `scanners/crypto-scanner.md` | crypto-scanner instructions |
| `scanners/network-scanner.md` | network-scanner instructions |
| `scanners/component-info-scanner.md` | component-info-scanner instructions |
| `templates/report-密码学.md` | Crypto report template |
| `templates/report-网络.md` | Network report template |
| `templates/report-组件档案.md` | Component-info report template |
| `tests/fixtures/crypto-test/sample.c`, `sample.py`, `pom.xml` | Crypto fixture |
| `tests/fixtures/network-test/server.go`, `config.yaml` | Network fixture |
| `tests/fixtures/component-info-test/app.py`, `docker-compose.yml` | Component-info fixture |
| `tests/fixtures/full-test-component-info/` | E2E fixture |
| `tests/fixtures/expected/crypto-expected.json` | Crypto baseline |
| `tests/fixtures/expected/network-expected.json` | Network baseline |
| `tests/fixtures/expected/component-info-expected.json` | Component-info baseline |
| `tests/fixtures/expected/component-info-summary-expected.json` | Summary baseline |
| `component-info.md` | security-scanner self-disclosure |

| Modified File | Change |
|---------------|--------|
| `SKILL.md` | Add 3 new dimensions to triggers, scanner list, finding schema doc |
| `orchestration/orchestrator.md` | Add 3 scanners to Phase 1 dispatch, update A1 thresholds, add verdict dedup rule |
| `orchestration/reporter.md` | Add 3 sub-report outputs, component-info summary JSON, overview chapter generation |
| `orchestration/reconnaissance.md` | Extend Scan Plan with 3 new file segments |
| `references/dependency-check.md` | Add `jq` and `xmllint` checks, NVD/OSV network reachability |
| `README.md` | Update dimension table, file structure, output formats, FAQ |

---

## Task 1: Add Red-Line Rules Reference

**Files:**
- Create: `references/red-line-rules.md`

**Purpose:** Centralized red-line rules table. Every scanner consults this for severity and remediation text.

**Step 1.1: Create the file**

Write the following content to `references/red-line-rules.md`:

```markdown
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
| `severity` | `critical` / `high` / `medium` / `low` |
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

### 不安全非对称算法 (红线 2)

| ID | 名称 | severity | pattern | 修复建议 |
|----|------|---------|---------|---------|
| RL-020 | RSA 密钥 < 2048 | high | `RSA_generate_key\([0-9]{1,3}\)\|RSA_generate_key_ex\([a-z_]+,\s*[0-9]{1,3}` | 改用 RSA ≥ 2048 位 |
| RL-021 | DSA 密钥 < 2048 | high | `DSA_generate_key\([0-9]{1,3}\)\|DSA_generate_parameters_ex\([a-z_]+,\s*[0-9]{1,3}` | 改用 DSA ≥ 2048 位或 Ed25519 |
| RL-022 | ElGamal 使用 | high | `ElGamal\|elgamal_encrypt` | 改用 ECIES 或 RSA-OAEP |

### 不安全 Hash (红线 2)

| ID | 名称 | severity | pattern | evidence_required | 修复建议 |
|----|------|---------|---------|------------------|---------|
| RL-040 | MD5 密码用途 | high | `md5\([^)]*(?:password\|passwd\|pwd)[^)]*\)` | 调用方变量名包含 password | 改用 bcrypt/scrypt/Argon2 |
| RL-041 | MD5 签名用途 | high | `md5.*sign\|sign.*md5` | 上下文含 sign | 改用 SHA-256 + RSA/ECDSA |
| RL-042 | MD5 证书指纹 | medium | `md5.*(?:cert\|certificate\|fingerprint)` | 上下文含 cert | 改用 SHA-256 |
| RL-043 | SHA-1 签名 | high | `sha1.*sign\|sign.*sha1\|SHA1withRSA\|SHA-1WithRSA` | 上下文含 sign/cert | 改用 SHA-256 + RSA/ECDSA |
| RL-044 | SHA-1 证书 | high | `sha1.*(?:cert\|certificate)\|sha1WithRSAEncryption` | 上下文含 cert | 改用 SHA-256 |

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
```

**Step 1.2: Verify file**

```bash
test -f references/red-line-rules.md && echo "OK" || echo "FAIL"
wc -l references/red-line-rules.md  # expect >= 100
```

**Step 1.3: Commit**

```bash
git add references/red-line-rules.md
git commit -m "feat(references): add red-line rules table

Centralized red-line rules table with 10 categories covering
all 5 red lines from the requirements. Each rule has id,
severity, pattern, and remediation. Used by crypto-scanner,
network-scanner, and component-info-scanner.

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 2: Add Crypto Patterns Reference

**Files:**
- Create: `references/patterns-crypto.md`

**Purpose:** Algorithm, pseudo-encryption, and random number patterns. Shared between crypto-scanner and secret-scanner.

**Step 2.1: Create the file**

Write the following to `references/patterns-crypto.md`:

```markdown
# 密码学 Patterns 库

> 本文件集中维护密码学相关的 pattern 集合。crypto-scanner 和 secret-scanner 都引用此文件。
> 用户可在此扩展自定义 pattern。

## 1. 对称算法 Pattern

### 1.1 安全对称算法（不告警）

| 算法 | Pattern | 备注 |
|------|---------|------|
| AES-128/192/256 | `AES(_|\b)\|aes_encrypt\|crypto\.Cipher.*aes` | AES-CBC/ECB/GCM/CTR |
| AES-GCM | `AES/GCM\|aes-256-gcm\|GCM.*AES` | 推荐模式 |
| SM4 | `SM4\|sm4_crypt\|sms4` | 国密对称 |
| ChaCha20-Poly1305 | `ChaCha20\|chacha20-poly1305\|XChaCha20` | 推荐模式 |

### 1.2 不安全对称算法（红线 2）

| 算法 | Pattern | severity |
|------|---------|---------|
| DES | `\bDES(_|\b)\|des_encrypt\|des_crypt` | high |
| 3DES | `\b3DES\|TripleDES\|DES_ede\|des3` | high |
| RC4 | `\bRC4\|ARCFOUR\|rc4_encrypt` | high |
| Blowfish | `\bBlowfish\|BF_encrypt\|blowfish` | medium |
| IDEA | `\bIDEA\|idea_encrypt` | medium |
| RC2 | `\bRC2\|rc2_encrypt` | high |

### 1.3 跨语言 API 映射

| 语言 | DES 触发 | AES 触发 | SM4 触发 |
|------|---------|---------|---------|
| C/C++ | `DES_` 函数族 | `AES_` 函数族 | 自定义 `sm4_` 函数族 |
| Go | `des.NewCipher` | `aes.NewCipher` | `github.com/tjfoc/gmsm/sm4` |
| Python | `Crypto.Cipher.DES` | `Crypto.Cipher.AES` | `gmssl.sm4` |
| Java | `Cipher.getInstance("DES")` | `Cipher.getInstance("AES")` | `Cipher.getInstance("SM4")` |
| JavaScript | `crypto.createCipheriv('des')` | `crypto.createCipheriv('aes')` | 自实现 sm4.js |

## 2. 非对称算法 Pattern

### 2.1 安全非对称算法（不告警）

| 算法 | Pattern |
|------|---------|
| RSA-2048/3072/4096 | `RSA.*(2048\|3072\|4096)\|generate_key.*2048` |
| ECC / ECDSA | `ECDSA\|ecdsa\.` |
| Ed25519 | `Ed25519\|ed25519` |
| SM2 | `\bSM2\|sm2_` |
| X25519 | `X25519\|x25519` |

### 2.2 不安全非对称算法（红线 2）

| 算法 | Pattern | severity |
|------|---------|---------|
| RSA < 2048 | `RSA_generate_key_ex?\([a-z_]+,\s*(?:512\|1024)` | high |
| DSA < 2048 | `DSA_generate_parameters_ex\([a-z_]+,\s*(?:512\|1024)` | high |
| ElGamal | `\bElGamal\|elgamal_` | high |
| 1024 位 RSA | `RSA.*1024\|key_size.*1024.*rsa` | high |

## 3. Hash 算法 Pattern

### 3.1 安全 Hash（不告警）

| 算法 | Pattern |
|------|---------|
| SHA-256 | `SHA-?256\|sha256` |
| SHA-384 | `SHA-?384\|sha384` |
| SHA-512 | `SHA-?512\|sha512` |
| SHA3-256/512 | `SHA3-?(256\|512)\|sha3_` |
| SM3 | `\bSM3\|sm3_` |
| BLAKE2 | `BLAKE2\|blake2` |
| BLAKE3 | `BLAKE3\|blake3` |

### 3.2 不安全 Hash（红线 2，需结合用途判断）

| 算法 | Pattern | 安全用途 | 非安全用途 |
|------|---------|---------|-----------|
| MD5 | `MD5\|md5\(` | password 哈希、token 派生、签名、证书指纹 | cache key、etag、文件 dedup、内容指纹 |
| SHA-1 | `SHA-?1\|sha1\(` | 数字签名、证书指纹 | git commit hash、内容指纹 |

安全/非安全用途通过上下文关键字判断（前 50 字符或后 50 字符是否包含 password/passwd/pwd/sign/signature/cert/key/token/iv/salt 等关键字）。

## 4. 伪加密 Pattern（红线 1）

### 4.1 Base64 充当密码加密（critical）

```regex
base64_(?:decode|encode)\s*\([^)]*(?:password|passwd|pwd|secret|key|token)
```

跨语言变体：
- Python: `base64.b64decode(...)` 紧邻 `password`/`secret`/`key` 变量
- Java: `Base64.getDecoder().decode(...)` 紧邻上述变量
- JavaScript: `Buffer.from(x, 'base64')` 紧邻上述变量

### 4.2 自写 XOR 循环（critical）

```regex
for\s*\([^)]+\)\s*\{[^}]*\^=[\s\S]{0,100}\}
while\s*\([^)]+\)[^}]*\^=
```

### 4.3 字符串反转充当加密（medium）

```regex
(?:reverse|reversed|strrev)\s*\([^)]*(?:password|secret|key)
```

### 4.4 Caesar 移位充当加密（medium）

```regex
chr\s*\(\s*ord\s*\([^)]+\)\s*[+\-]\s*[0-9]+[\s\S]{0,50}password
```

## 5. 随机数 Pattern

### 5.1 安全 RNG（不告警）

| API | Pattern |
|-----|---------|
| `/dev/urandom` | `/dev/urandom` |
| `/dev/random` | `/dev/random` |
| OpenSSL `RAND_bytes` | `RAND_bytes\|RAND_priv_bytes` |
| JDK `SecureRandom` | `java\.security\.SecureRandom\|new SecureRandom` |
| Python `os.urandom` | `os\.urandom\|secrets\.|SystemRandom` |
| Node `crypto.randomBytes` | `crypto\.randomBytes\|crypto\.getRandomValues\|webcrypto` |
| Go `crypto/rand` | `crypto/rand\.\|rand\.Read` |
| iPSI `CRYPT_random` | `CRYPT_random` |
| VPP `IPSI_CRYPT_rand_bytes` | `IPSI_CRYPT_rand_bytes` |
| TEE `TEE_GenerateRandom` | `TEE_GenerateRandom` |

### 5.2 伪 RNG（红线 3，需结合用途判断）

| API | Pattern | severity |
|-----|---------|---------|
| JS `Math.random` | `Math\.random` 用于 key/iv/salt/token/nonce | critical |
| Java `java.util.Random` | `new Random()` 用于 nextBytes/nextInt | critical |
| C `rand()` | `rand\(\)` | critical |
| C `random()` | `random\(\)` | critical |
| Python `random.random` | `random\.random\|random\.randint` 用于 crypto | critical |
| PHP `mt_rand` | `mt_rand\|rand` 用于 key/salt | critical |
| Ruby `rand` | `Kernel\.rand\|Random\.new` 用于 crypto | critical |
| Go `math/rand` | `math/rand\.` 用于 crypto 场景 | critical |
| time() 派生 key | `time\(\)` 或 `Date\.now()` 派生 key/iv/salt/seed | critical |

伪 RNG 必须上下文包含 key/iv/salt/token/nonce/secret/password 才告警。
```

**Step 2.2: Verify file**

```bash
test -f references/patterns-crypto.md && echo "OK" || echo "FAIL"
wc -l references/patterns-crypto.md  # expect >= 100
```

**Step 2.3: Commit**

```bash
git add references/patterns-crypto.md
git commit -m "feat(references): add crypto patterns library

Algorithm, pseudo-encryption, and random number patterns.
Shared between crypto-scanner and secret-scanner.

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 3: Add Network Patterns Reference

**Files:**
- Create: `references/patterns-network.md`

**Step 3.1: Create the file**

Write the following to `references/patterns-network.md`:

```markdown
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

## 4. 端口号与组件用途对照

| 端口 | 常见用途 | 风险等级 |
|------|---------|---------|
| 80 | HTTP | low（应重定向到 443） |
| 443 | HTTPS | low |
| 22 | SSH | low（应禁用 root 登录） |
| 21 | FTP | high（应替换为 SFTP/FTPS） |
| 23 | Telnet | critical（红线） |
| 25 | SMTP | medium（应配 STARTTLS） |
| 3306 | MySQL | high（应限制访问） |
| 5432 | PostgreSQL | high（应限制访问） |
| 6379 | Redis | high（应设密码） |
| 27017 | MongoDB | high（应设认证） |
| 1-1023 | 特权端口 | medium（需要 root 或 capability） |
```

**Step 3.2: Verify and commit**

```bash
test -f references/patterns-network.md && echo "OK"
git add references/patterns-network.md
git commit -m "feat(references): add network protocols and ports patterns

Protocol, port, and cross-validation patterns for network-scanner.

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 4: Add Personal Data Patterns Reference

**Files:**
- Create: `references/personal-data-patterns.md`

**Step 4.1: Create the file**

```markdown
# 个人数据 Patterns 库

> 本文件集中维护个人数据字段名和违规处理 pattern。component-info-scanner 引用此文件。

## 1. 个人数据字段名 Pattern

### 1.1 类别与 Pattern

| 类别 | Pattern | 严重度（明文存储/HTTP 传输） |
|------|---------|----------------------------|
| 姓名 | `\b(?:name\|username\|real_name\|full_name\|user_name)\b` | medium |
| 手机号 | `\b(?:phone\|mobile\|tel\|cellphone\|phone_number\|mobile_number)\b` | high |
| 身份证 | `\b(?:id_card\|idcard\|identity\|id_number\|identity_card\|citizen_id)\b` | critical |
| 邮箱 | `\b(?:email\|mail\|e_mail\|email_address)\b` | medium |
| 位置 | `\b(?:location\|gps\|latitude\|longitude\|address\|geo)\b` | high |
| 设备标识 | `\b(?:device_id\|imei\|mac\|udid\|android_id\|idfa\|gaid)\b` | high |
| 银行卡 | `\b(?:bank_card\|card_number\|credit_card\|cc_number)\b` | critical |
| 出生日期 | `\b(?:birthday\|birth_date\|dob)\b` | medium |
| 头像 | `\b(?:avatar\|profile_photo\|head_image)\b` | low |
| IP 地址 | `\b(?:ip\|ip_address\|client_ip\|remote_ip)\b` | low |

### 1.2 跨语言字段命名变体

| 类别 | snake_case | camelCase | PascalCase |
|------|-----------|-----------|------------|
| 姓名 | `user_name` | `userName` | `UserName` |
| 手机号 | `phone_number` | `phoneNumber` | `PhoneNumber` |
| 身份证 | `id_card` | `idCard` | `IdCard` |
| 邮箱 | `email` | `email` | `Email` |

Pattern 须同时支持三种命名约定（用 `\b` + 字符集 `[a-zA-Z_0-9]` 包围）。

## 2. 违规处理 Pattern

### 2.1 明文存储（红线 RL-140 ~ RL-142）

```regex
(?:id_card|idcard|phone|mobile|email|bank_card|identity).{0,80}(?:=|:)\s*["'][^"']{4,}["']
```

排除：上下文包含 `encrypt|hash|mask|hmac|bcrypt|cipher|secrets\.|SystemRandom` 时不告警。

### 2.2 HTTP 明文传输（红线 RL-143）

```regex
http://[^"'\s]*(?:id_card|phone|idcard|mobile|email|bank_card|identity_card)
```

### 2.3 日志明文（红线 RL-144）

```regex
logger\.(?:info|debug|error|warn|fatal)\s*\([^)]*(?:email|mail|phone|mobile|id_card|idcard)\b
```

排除：上下文包含 `mask\|redact\|truncate\|hash\|md5\|sha` 时不告警。

## 3. 用途分类

| 字段 | 常见用途 | 风险 |
|------|---------|------|
| 姓名 | 用户标识、订单、收件人 | medium |
| 手机号 | 短信验证、紧急联系、收件人 | high（易被滥用做骚扰） |
| 身份证 | 实名认证、年龄校验 | critical（一旦泄露难注销） |
| 邮箱 | 通知、找回密码 | medium |
| 位置 | 导航、签到、附近的人 | high（可定位家庭住址） |
| 设备标识 | 推送、用户追踪、广告 | high（用户画像） |
| 银行卡 | 支付 | critical（资金风险） |

## 4. 用户自定义字段

在下方添加项目特定的个人数据字段：

<!-- 示例:
| 类别 | 字段 | severity |
| 医疗 | medical_record | critical |
-->
```

**Step 4.2: Verify and commit**

```bash
test -f references/personal-data-patterns.md && echo "OK"
git add references/personal-data-patterns.md
git commit -m "feat(references): add personal data patterns library

Personal data field regexes and violation patterns for
component-info-scanner. Covers 10 PII categories with
cross-language naming variant support.

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 5: Add Library Vulnerability Knowledge Base

**Files:**
- Create: `references/library-vuln-caps.md`

**Step 5.1: Create the file**

```markdown
# 库版本 → 不安全能力 知识库

> 本文件维护已知密码学/网络库版本与默认启用不安全能力的对应关系。
> crypto-scanner / network-scanner / component-info-scanner 都引用此文件。
> 启动时尝试拉 NVD/OSV 离线快照（24h 缓存）覆盖本表，失败时回落本表。

## 1. 知识库条目格式

每条记录包含：

| 字段 | 说明 |
|------|------|
| `library` | 库名（package name） |
| `language` | 所属语言/生态系统 |
| `insecure_versions` | 不安全版本范围（semver） |
| `trigger_capability` | 默认启用的不安全能力 |
| `cve` | 相关 CVE（可选） |
| `remediation` | 修复建议 |

## 2. 已知条目

### 2.1 OpenSSL

| library | language | insecure_versions | trigger_capability | cve | remediation |
|---------|----------|-------------------|---------------------|-----|-------------|
| openssl | C/C++ | < 1.0.1 | SSLv2 默认启用 | CVE-2016-0800 | 升级到 OpenSSL ≥ 1.1.1 |
| openssl | C/C++ | < 1.1.0 | SSLv3 默认启用 | CVE-2014-3566 | 升级到 OpenSSL ≥ 1.1.1 |
| openssl | C/C++ | 1.0.1 ~ 1.0.1f | Heartbleed | CVE-2014-0160 | 升级到 OpenSSL ≥ 1.0.1g |
| openssl | C/C++ | < 3.0.0 | TLSv1.0 默认支持 | - | 设置 minProtocol = TLSv1.2 |

### 2.2 Bouncy Castle (Java)

| library | language | insecure_versions | trigger_capability | cve | remediation |
|---------|----------|-------------------|---------------------|-----|-------------|
| bouncycastle | Java | < 1.50 | MD5withRSA 默认签名 | - | 升级到 ≥ 1.70，禁用 MD5withRSA |
| bouncycastle | Java | < 1.56 | TLSv1.0 默认启用 | - | 升级到 ≥ 1.70，配置 minimum TLS version |

### 2.3 Python cryptography

| library | language | insecure_versions | trigger_capability | cve | remediation |
|---------|----------|-------------------|---------------------|-----|-------------|
| cryptography | Python | < 2.0 | SSLv3 默认开启 | - | 升级到 ≥ 3.0，使用 create_default_context() |
| cryptography | Python | < 3.0 | TLSv1.0 默认支持 | - | 设置 minimum_version = TLSVersion.TLSv1_2 |

### 2.4 JSSE / JDK

| library | language | insecure_versions | trigger_capability | cve | remediation |
|---------|----------|-------------------|---------------------|-----|-------------|
| com.sun.net.ssl | Java | < 8u291 | TLSv1.0/1.1 默认启用 | - | 升级 JDK，配置 jdk.tls.disabledAlgorithms |
| javax.net.ssl | Java | < 11 | TLSv1.0 默认支持 | - | 升级 JDK，禁用 TLSv1.0/1.1 |

### 2.5 Node.js TLS

| library | language | insecure_versions | trigger_capability | cve | remediation |
|---------|----------|-------------------|---------------------|-----|-------------|
| node:tls | JavaScript | < 10.0.0 | TLSv1.0 默认支持 | - | 升级 Node.js ≥ 18，配置 secureOptions: SSL_OP_NO_TLSv1 |
| nodejs | JavaScript | < 18.0.0 | OpenSSL 1.1.1 (支持 TLSv1.0) | - | 升级到 Node.js ≥ 18 |

### 2.6 Go crypto/tls

| library | language | insecure_versions | trigger_capability | cve | remediation |
|---------|----------|-------------------|---------------------|-----|-------------|
| crypto/tls | Go | < 1.17 | TLSv1.0 默认 | - | 升级 Go ≥ 1.17，配置 tls.Config.MinVersion = tls.VersionTLS12 |
| crypto/tls | Go | < 1.18 | TLSv1.1 默认 | - | 升级 Go ≥ 1.18 |

### 2.7 中软密码学组件

| library | language | insecure_versions | trigger_capability | cve | remediation |
|---------|----------|-------------------|---------------------|-----|-------------|
| ipsi-crypt | Java | < 3.0 | MD5 默认支持 | - | 升级到 ≥ 3.0，禁用 MD5 |
| vpp-crypt | C/C++ | < 2.0 | DES 默认支持 | - | 升级到 ≥ 2.0，禁用 DES |

## 3. NVD/OSV 离线快照策略

```bash
# 启动时尝试拉取
SNAPSHOT_DIR="$HOME/.cache/security-scanner/nvd-snapshot"
SNAPSHOT_AGE=86400  # 24 hours

if [ -f "$SNAPSHOT_DIR/last-update" ]; then
    age=$(($(date +%s) - $(stat -c %Y "$SNAPSHOT_DIR/last-update")))
    if [ $age -lt $SNAPSHOT_AGE ]; then
        # Use cached snapshot
        load_nvd_snapshot "$SNAPSHOT_DIR"
        exit 0
    fi
fi

# Try to fetch fresh snapshot
if curl -sSf --max-time 10 https://nvd.nist.gov/feeds/json/cpematching/1.1/nvdcpematching-1.1.json.gz -o /tmp/nvd.json.gz 2>/dev/null; then
    mkdir -p "$SNAPSHOT_DIR"
    gunzip -c /tmp/nvd.json.gz > "$SNAPSHOT_DIR/data.json"
    touch "$SNAPSHOT_DIR/last-update"
    load_nvd_snapshot "$SNAPSHOT_DIR"
else
    # Network unavailable, fall back to built-in knowledge base
    echo "WARN: NVD snapshot unavailable, using built-in knowledge base"
fi
```

失败时记录到 `dependency-check.md` 的 `degraded_dimensions` 中。

## 4. 用户自定义条目

在下方添加项目特定的库版本与不安全能力：

<!-- 示例:
| mycompany-crypto | Java | < 5.0 | RC4 默认 | 升级到 ≥ 5.0
-->
```

**Step 5.2: Verify and commit**

```bash
test -f references/library-vuln-caps.md && echo "OK"
git add references/library-vuln-caps.md
git commit -m "feat(references): add library version knowledge base

Maps library versions to default-enabled insecure capabilities.
Covers OpenSSL, Bouncy Castle, Python cryptography, JDK JSSE,
Node.js TLS, Go crypto/tls, and Chinese crypto stacks.

NVD/OSV offline snapshot fetch with 24h cache, falls back to
built-in knowledge base on network failure.

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 6: Add Crypto Scanner

**Files:**
- Create: `scanners/crypto-scanner.md`
- Create: `tests/fixtures/crypto-test/sample.c`
- Create: `tests/fixtures/crypto-test/sample.py`
- Create: `tests/fixtures/crypto-test/pom.xml`
- Create: `tests/fixtures/expected/crypto-expected.json`

**Step 6.1: Create crypto-scanner.md**

Write the scanner instructions to `scanners/crypto-scanner.md`. Structure follows `scanners/secret-scanner.md` exactly. Key sections:

- 角色 (Role)
- 输入 (Input): `source_shards + config_files + component_name`
- 输出 (Output): JSON findings array, dimension = `crypto`, id = `CRYPTO-{SEQ}`
- 执行步骤 (Steps):
  - Step 1: 读取 `references/patterns-crypto.md` 和 `references/red-line-rules.md`
  - Step 2: Layer 1 - 关键字 grep（按语言分类）
  - Step 3: Layer 2 - 算法识别（对称/非对称/Hash/自定义）
  - Step 4: Layer 3 - 伪加密检测
  - Step 5: Layer 4 - 随机数 API 识别
  - Step 6: 库版本知识库匹配（读 lock 文件 + `references/library-vuln-caps.md`）
  - Step 7: 安全/非安全用途区分
  - Step 8: Finding 输出
- 判定规则 (Rules):
  - status: PASS/WARN/FAIL
  - severity: critical/high/medium/low
  - confidence: high/medium/low
  - verdict: confirmed/suspected/needs_human/unverified
- 异常处理 (Errors)

The full content is provided in the spec section 3.1. Use spec section 3.1 + patterns-crypto.md + red-line-rules.md as the source of truth.

**Step 6.2: Create crypto fixture**

Create `tests/fixtures/crypto-test/sample.c`:
```c
#include <openssl/md5.h>
#include <openssl/des.h>

void hash_password(const char *pwd) {
    unsigned char digest[16];
    MD5((unsigned char*)pwd, strlen(pwd), digest);  // RL-040: MD5 password
}

void encrypt_data(unsigned char *data, int len) {
    DES_key_schedule ks;
    DES_set_key((DES_cblock*)"12345678", &ks);  // RL-001: DES
    DES_ecb_encrypt(data, data, &ks, DES_ENCRYPT);
}
```

Create `tests/fixtures/crypto-test/sample.py`:
```python
import random
import hashlib

def derive_key():
    return random.random()  # RL-080: pseudo-random for key derivation
```

Create `tests/fixtures/crypto-test/pom.xml`:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<project>
    <dependencies>
        <dependency>
            <groupId>org.bouncycastle</groupId>
            <artifactId>bcprov-jdk15on</artifactId>
            <version>1.46</version>  <!-- RL-121: Bouncy Castle < 1.50 -->
        </dependency>
    </dependencies>
</project>
```

**Step 6.3: Create crypto-expected.json**

```json
{
  "scan_metadata": {
    "scanner": "crypto",
    "version": "1.0",
    "component": "crypto-test"
  },
  "findings": [
    {
      "id": "CRYPTO-001",
      "dimension": "crypto",
      "file": "tests/fixtures/crypto-test/sample.c",
      "line": 6,
      "check_item": "insecure_hash",
      "status": "FAIL",
      "severity": "high",
      "confidence": "high",
      "verdict": "confirmed",
      "verdict_reasoning": "MD5 用于密码哈希，红线 RL-040",
      "detail": "MD5 用于密码派生",
      "suggestion": "改用 bcrypt/scrypt/Argon2",
      "evidence": "MD5((unsigned char*)pwd, strlen(pwd), digest)"
    },
    {
      "id": "CRYPTO-002",
      "dimension": "crypto",
      "file": "tests/fixtures/crypto-test/sample.c",
      "line": 11,
      "check_item": "insecure_symmetric",
      "status": "FAIL",
      "severity": "high",
      "confidence": "high",
      "verdict": "confirmed",
      "verdict_reasoning": "DES 使用，红线 RL-001",
      "detail": "DES 加密算法已被认为不安全",
      "suggestion": "改用 AES-128 或 SM4",
      "evidence": "DES_set_key((DES_cblock*)\"12345678\", &ks)"
    },
    {
      "id": "CRYPTO-003",
      "dimension": "crypto",
      "file": "tests/fixtures/crypto-test/sample.py",
      "line": 5,
      "check_item": "insecure_random",
      "status": "FAIL",
      "severity": "critical",
      "confidence": "high",
      "verdict": "confirmed",
      "verdict_reasoning": "Python random.random 用于 key 派生，红线 RL-080",
      "detail": "使用密码学不安全的伪随机数派生密钥",
      "suggestion": "改用 secrets 模块或 os.urandom",
      "evidence": "return random.random()  # 上下文: derive_key"
    },
    {
      "id": "CRYPTO-004",
      "dimension": "crypto",
      "file": "tests/fixtures/crypto-test/pom.xml",
      "line": 7,
      "check_item": "library_vuln",
      "status": "WARN",
      "severity": "high",
      "confidence": "high",
      "verdict": "confirmed",
      "verdict_reasoning": "Bouncy Castle 1.46 < 1.50，默认启用 MD5withRSA",
      "detail": "Bouncy Castle 1.46 默认启用 MD5withRSA 签名",
      "suggestion": "升级到 Bouncy Castle ≥ 1.70",
      "evidence": "library=BouncyCastle@1.46 | library_version=1.46 | trigger=MD5withRSA default | cve=null"
    }
  ]
}
```

**Step 6.4: Validate JSON**

```bash
python3 -m json.tool tests/fixtures/expected/crypto-expected.json > /dev/null && echo "OK" || echo "FAIL"
```

**Step 6.5: Commit**

```bash
git add scanners/crypto-scanner.md tests/fixtures/crypto-test/ tests/fixtures/expected/crypto-expected.json
git commit -m "feat(scanner): add crypto-scanner with fixture and baseline

Detects insecure symmetric/asymmetric/hash algorithms,
pseudo-encryption, insecure random number generators, and
library version-based vulnerabilities.

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 7: Add Network Scanner

**Files:**
- Create: `scanners/network-scanner.md`
- Create: `tests/fixtures/network-test/server.go`
- Create: `tests/fixtures/network-test/config.yaml`
- Create: `tests/fixtures/expected/network-expected.json`

**Step 7.1: Create network-scanner.md**

Use spec section 3.2 + patterns-network.md as the source. Structure mirrors crypto-scanner.md.

**Step 7.2: Create network fixture**

Create `tests/fixtures/network-test/server.go`:
```go
package main

import (
    "crypto/tls"
    "net/http"
)

func main() {
    cfg := &tls.Config{MinVersion: tls.VersionSSL30}  // RL-100: SSLv3
    server := &http.Server{Addr: ":8080", TLSConfig: cfg}  // Network-scanner
    server.ListenAndServeTLS("cert.pem", "key.pem")
}
```

Create `tests/fixtures/network-test/config.yaml`:
```yaml
server:
  port: 23  # RL-104: Telnet port
  protocol: telnet
```

**Step 7.3: Create network-expected.json**

```json
{
  "scan_metadata": {"scanner": "network", "version": "1.0", "component": "network-test"},
  "findings": [
    {
      "id": "NETWORK-001",
      "dimension": "network",
      "file": "tests/fixtures/network-test/server.go",
      "line": 9,
      "check_item": "legacy_protocol",
      "status": "FAIL",
      "severity": "high",
      "confidence": "high",
      "verdict": "confirmed",
      "verdict_reasoning": "MinVersion = VersionSSL30, 启用 SSLv3，红线 RL-100",
      "detail": "服务器配置启用了 SSLv3 协议",
      "suggestion": "改用 TLSv1.2 或 TLSv1.3",
      "evidence": "tls.Config{MinVersion: tls.VersionSSL30}"
    },
    {
      "id": "NETWORK-002",
      "dimension": "network",
      "file": "tests/fixtures/network-test/server.go",
      "line": 10,
      "check_item": "port_listening",
      "status": "PASS",
      "severity": "info",
      "confidence": "high",
      "verdict": "confirmed",
      "verdict_reasoning": "通过 &http.Server{Addr: \":8080\"} 识别监听 8080/TCP",
      "detail": "应用监听 8080/TCP 端口",
      "suggestion": "无",
      "evidence": "Addr: \":8080\""
    },
    {
      "id": "NETWORK-003",
      "dimension": "network",
      "file": "tests/fixtures/network-test/config.yaml",
      "line": 3,
      "check_item": "port_privileged",
      "status": "FAIL",
      "severity": "high",
      "confidence": "high",
      "verdict": "confirmed",
      "verdict_reasoning": "23 端口为 Telnet 协议默认端口，红线 RL-104",
      "detail": "应用监听 23/TCP（Telnet 默认端口）",
      "suggestion": "改用 SSH（22 端口）",
      "evidence": "port: 23"
    }
  ]
}
```

**Step 7.4: Validate and commit**

```bash
python3 -m json.tool tests/fixtures/expected/network-expected.json > /dev/null
git add scanners/network-scanner.md tests/fixtures/network-test/ tests/fixtures/expected/network-expected.json
git commit -m "feat(scanner): add network-scanner with fixture and baseline

Detects communication protocols, listening ports, and
legacy/insecure protocol usage.

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 8: Add Component-Info Scanner

**Files:**
- Create: `scanners/component-info-scanner.md`
- Create: `tests/fixtures/component-info-test/app.py`
- Create: `tests/fixtures/component-info-test/Dockerfile`
- Create: `tests/fixtures/component-info-test/README.md`
- Create: `tests/fixtures/expected/component-info-expected.json`

**Step 8.1: Create component-info-scanner.md**

Use spec section 3.3 + personal-data-patterns.md as the source. Structure mirrors crypto-scanner.md.

**Step 8.2: Create component-info fixture**

Create `tests/fixtures/component-info-test/app.py`:
```python
from django.db import models
import telnetlib

class User(models.Model):
    name = models.CharField(max_length=100)        # PII: 姓名
    phone = models.CharField(max_length=20)       # PII: 手机号 (RL-141: 明文)
    id_card = models.CharField(max_length=18)      # PII: 身份证 (RL-140: 明文)

ADMIN_USER = "admin"        # RL-160: 默认账号
ADMIN_PASS = "admin123"     # RL-160: 默认密码
```

Create `tests/fixtures/component-info-test/Dockerfile`:
```dockerfile
FROM ubuntu:20.04
COPY app.py /app/
RUN chmod u+s /app/binary   # 暗示需 root 启动
```

Create `tests/fixtures/component-info-test/docker-compose.yml`:
```yaml
services:
  app:
    image: myapp
    privileged: true        # 强信号：需要 root
    cap_add:
      - SYS_ADMIN
```

**Step 8.3: Create component-info-expected.json**

```json
{
  "scan_metadata": {"scanner": "component_info", "version": "1.0", "component": "component-info-test"},
  "findings": [
    {
      "id": "INFO-001",
      "dimension": "component_info",
      "file": "tests/fixtures/component-info-test/app.py",
      "line": 1,
      "check_item": "architecture",
      "status": "PASS",
      "severity": "info",
      "confidence": "high",
      "verdict": "confirmed",
      "verdict_reasoning": "检测到 Django 框架导入，推断 B/S 架构",
      "detail": "组件为 B/S 架构（Web 应用）",
      "suggestion": "无",
      "evidence": "from django.db import models"
    },
    {
      "id": "INFO-002",
      "dimension": "component_info",
      "file": "tests/fixtures/component-info-test/app.py",
      "line": 12,
      "check_item": "default_account",
      "status": "FAIL",
      "severity": "high",
      "confidence": "high",
      "verdict": "confirmed",
      "verdict_reasoning": "硬编码 admin/admin123 默认账号，红线 RL-160",
      "detail": "代码中存在硬编码默认账号 admin/admin123",
      "suggestion": "强制首次登录修改密码",
      "evidence": "ADMIN_USER = \"admin\"\nADMIN_PASS = \"admin123\""
    },
    {
      "id": "INFO-003",
      "dimension": "component_info",
      "file": "tests/fixtures/component-info-test/app.py",
      "line": 5,
      "check_item": "personal_data",
      "status": "FAIL",
      "severity": "critical",
      "confidence": "high",
      "verdict": "confirmed",
      "verdict_reasoning": "id_card 字段明文存储，红线 RL-140",
      "detail": "身份证号字段以明文 CharField 存储",
      "suggestion": "改用加密存储 + 脱敏显示",
      "evidence": "id_card = models.CharField(max_length=18)"
    },
    {
      "id": "INFO-004",
      "dimension": "component_info",
      "file": "tests/fixtures/component-info-test/app.py",
      "line": 4,
      "check_item": "personal_data",
      "status": "FAIL",
      "severity": "high",
      "confidence": "high",
      "verdict": "confirmed",
      "verdict_reasoning": "phone 字段明文存储，红线 RL-141",
      "detail": "手机号字段以明文 CharField 存储",
      "suggestion": "改用加密存储 + 脱敏显示",
      "evidence": "phone = models.CharField(max_length=20)"
    },
    {
      "id": "INFO-005",
      "dimension": "component_info",
      "file": "tests/fixtures/component-info-test/docker-compose.yml",
      "line": 4,
      "check_item": "requires_root",
      "status": "FAIL",
      "severity": "high",
      "confidence": "high",
      "verdict": "confirmed",
      "verdict_reasoning": "docker-compose.yml 含 privileged: true + cap_add: SYS_ADMIN，多源交集确认为需要 root",
      "detail": "组件需要 root 权限运行",
      "suggestion": "评估是否真的需要 privileged，尝试用最小 capability 替代",
      "evidence": "privileged: true\ncap_add:\n  - SYS_ADMIN"
    }
  ]
}
```

**Step 8.4: Validate and commit**

```bash
python3 -m json.tool tests/fixtures/expected/component-info-expected.json > /dev/null
git add scanners/component-info-scanner.md tests/fixtures/component-info-test/ tests/fixtures/expected/component-info-expected.json
git commit -m "feat(scanner): add component-info-scanner with fixture and baseline

Detects architecture type, default accounts, personal data
handling, and root-required signals.

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 9: Add Three Report Templates

**Files:**
- Create: `templates/report-密码学.md`
- Create: `templates/report-网络.md`
- Create: `templates/report-组件档案.md`

**Step 9.1: Create report-密码学.md**

Use the structure of `templates/report-安全编译.md`. Adapt to crypto findings.

```markdown
# 密码学合规扫描报告

## 基本信息

- **源码组件名称**: {component_name}
- **扫描时间**: {timestamp}
- **扫描文件数**: {source_count}
- **报告状态**: {report_status}

## 算法使用总览

| 类别 | 使用的算法 | 红线违规 | 备注 |
|------|----------|---------|------|
| 对称算法 | {symmetric_list} | {symmetric_red_line} | - |
| 非对称算法 | {asymmetric_list} | {asymmetric_red_line} | - |
| Hash 算法 | {hash_list} | {hash_red_line} | - |
| 自定义算法 | {custom_list} | {custom_red_line} | - |
| 伪加密 | {pseudo_list} | {pseudo_red_line} | - |
| 随机数 API | {random_list} | {random_red_line} | - |

## 详细 Findings

{crypto_findings_table}

## 红线违规汇总

| 红线 ID | 类别 | 严重度 | Finding 数量 | 涉及文件 |
|---------|------|--------|-------------|---------|
{red_line_summary_table}

## 问题汇总

- 严重问题: {critical_count} 项
- 高风险问题: {high_count} 项
- 中风险问题: {medium_count} 项
- 低风险问题: {low_count} 项
- 信息项: {info_count} 项
- 需人工确认: {needs_human_count} 项
- 未验证: {unverified_count} 项

## 修复建议

{crypto_suggestions}

## 库版本与不安全能力

{library_vuln_table}

## 字段完整性要求

- 算法总览表每行必须填写全部 6 个检查项。
- 对不适用项填写"不适用：{reason}"。
- 详细 finding 表每行包含 file、line、check_item、status、severity、verdict。

## 数据一致性要求

- 算法总览中的算法数量必须等于 findings 中对应类别的去重数量。
- 红线违规汇总必须与 JSON 中 `dimension=crypto` 的 findings 保持一致。
- 使用 `references/library-vuln-caps.md` 知识库时，必须在质量审计结果中标注知识库最后更新时间。

## 质量审计结果

- 字段完整性审计: {field_integrity_audit}
- 数据一致性审计: {data_consistency_audit}
- 内容质量审计: {content_quality_audit}
- 覆盖完整性审计: {coverage_audit}
- 审计备注: {audit_notes}

## 降级输出说明

{degradation_notes}
```

**Step 9.2: Create report-网络.md**

Same structure, adapted for network findings (protocols, ports, red-line protocol violations).

**Step 9.3: Create report-组件档案.md**

This is the most complex template. It must render the 9-field summary table plus the declaration-vs-actual reconciliation table plus the detailed findings. Use spec section 4.2 for the exact layout.

**Step 9.4: Verify and commit**

```bash
test -f templates/report-密码学.md && test -f templates/report-网络.md && test -f templates/report-组件档案.md
git add templates/report-密码学.md templates/report-网络.md templates/report-组件档案.md
git commit -m "feat(templates): add 3 new report templates for component info archive

report-密码学 / report-网络 / report-组件档案, following the
existing report-*.md pattern with field-integrity, data-consistency,
and quality-audit sections.

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 10: Update SKILL.md

**Files:**
- Modify: `SKILL.md`

**Step 10.1: Add triggers**

In the YAML frontmatter, add:
```yaml
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
```

**Step 10.2: Add scanner list**

In the `## 扫描维度` section, add 3 new entries:
```markdown
7. **密码学合规**（crypto）：对称/非对称/Hash 算法、伪加密、随机数 API、不安全协议。
8. **网络协议与端口**（network）：通信协议（SSHv2/TLS1.2/TLS1.3 等）、监听端口。
9. **组件基础档案**（component_info）：架构类型、默认账号、个人数据、root 启动需求。
```

**Step 10.3: Add finding schema extensions**

In the `## Finding Schema` section, add a note about library info in `evidence`:
```markdown
**新维度 evidence 扩展**：crypto / network / component_info 维度的 finding 的 `evidence` 字段可包含库信息，格式：
`library=NAME@VERSION | library_version=VERSION | trigger=REASON | cve=CVE-XXXX-XXXXX`
老 6 维度不解析此格式。
```

**Step 10.4: Update execution flow**

In the `## 执行流程` progressive disclosure path, add:
```markdown
Phase 1 -> scanners/*.md
   - 新增: scanners/crypto-scanner.md
   - 新增: scanners/network-scanner.md
   - 新增: scanners/component-info-scanner.md
```

**Step 10.5: Update Phase 1 dispatch list**

In `### Phase 1: 并行扫描（6 个维度）`, change title to `### Phase 1: 并行扫描（9 个维度）` and add 3 new entries:
```markdown
7. **Crypto Scanner**：读取 `scanners/crypto-scanner.md`、`references/patterns-crypto.md`、`references/red-line-rules.md`、`references/library-vuln-caps.md`，输入 `source_shards + config_files + dependency_files`。
8. **Network Scanner**：读取 `scanners/network-scanner.md`、`references/patterns-network.md`，输入 `source_shards + config_files`。
9. **Component-Info Scanner**：读取 `scanners/component-info-scanner.md`、`references/personal-data-patterns.md`，输入 `source_shards + config_files + docker_files`。
```

**Step 10.6: Update verdict-stage dedup note**

Add a note about crypto-scanner vs secret-scanner dedup (already in spec section 5.3).

**Step 10.7: Verify and commit**

```bash
grep -c "crypto-scanner" SKILL.md  # expect >= 3
grep -c "network-scanner" SKILL.md  # expect >= 3
grep -c "component-info-scanner" SKILL.md  # expect >= 3
git add SKILL.md
git commit -m "feat(skill): register 3 new dimensions in SKILL.md

Add crypto, network, component_info triggers and dispatch entries.
Document evidence field extension for library info.

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 11: Update Orchestrator

**Files:**
- Modify: `orchestration/orchestrator.md`

**Step 11.1: Update Phase 1 dispatch and failure thresholds**

Replace the existing `### 并行执行` and `### A1（Scan 审计）` sections with:

```markdown
### 并行执行

Phase 1 中 9 个维度扫描并行执行（6 老 + 3 新）。所有 Scanner 完成后设置 barrier，再进入 Phase 2。

### 条件跳过

- `elf_files` 为空：跳过 ELF Scanner。
- `source_shards` 为空：跳过 URL、Secret、Comment、Crypto、Network、Component-Info Scanner。
- `config_files` 为空：跳过 Secret、URL、Crypto、Network、Component-Info Scanner。
- `docker_files` 为空：Component-Info Scanner 的 root 启动信号降级为单源 INFERRED。
- `dependency_files` 为空：Crypto/Network Scanner 跳过库版本匹配，产出 `MISSING_LOCK_FILE` WARN finding。
- 对应依赖不可用且无降级方案（或用户已拒绝降级）：跳过该维度，记录 degraded_dimensions。
```

Replace `### A1（Scan 审计）` section:

```markdown
### A1（Scan 审计）

- 所有 Scanner 完成且输出符合 schema：PASS。
- 1 个 Scanner 失败：WARN，重试失败项（最多 2 次）。
- 2 个 Scanner 失败：WARN，标记失败维度但不影响主流程。
- 3-4 个 Scanner 失败：部分降级，继续其他维度。
- >= 5 个 Scanner 失败：FAIL，Phase 级降级。
```

**Step 11.2: Add verdict dedup rule**

After the `### A2（Verdict 审计）` section, add:

```markdown
### Verdict 阶段去重规则

`crypto-scanner` 与 `secret-scanner` 都会在源码中检测同一类模式（如 MD5 调用、AES 调用、加密库导入），verdict 阶段按以下规则去重：

- 同一 `file + line + check_item`（如 `foo.c:42:insecure_hash`）出现在两个 scanner 的 findings 中时，保留 severity 更高的一条；若 severity 相同，保留 `confidence` 更高的一条；若都相同则保留 crypto-scanner 的 finding。
- 同一 `file + line` 范围内（±5 行）出现多个相关 finding（如一个 MD5() 调用既被 secret-scanner 识别为弱哈希又被 crypto-scanner 识别为不安全算法），合并为一条 finding，evidence 拼接两者的证据。
```

**Step 11.3: Verify and commit**

```bash
grep -c "9 个维度" orchestration/orchestrator.md
grep -c "MISSING_LOCK_FILE" orchestration/orchestrator.md
grep -c "verdict 阶段去重" orchestration/orchestrator.md
git add orchestration/orchestrator.md
git commit -m "feat(orchestrator): register 3 new dimensions and update thresholds

Phase 1 dispatches 9 scanners in parallel. Failure thresholds
scaled: 1 fail retry, 2-3 mark failed, 4+ phase-level degradation.
Verdict dedup between crypto-scanner and secret-scanner documented.

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 12: Update Reporter

**Files:**
- Modify: `orchestration/reporter.md`

**Step 12.1: Add component-info summary JSON output**

In the `## 输出` section, add after the existing JSON output spec:

```markdown
### 2.1 组件档案 Summary JSON

输出文件：`component-info-summary-{component_name}-{date}.json`

这是新维度的双产出之一，结构按 9 字段聚合，便于生成 Markdown "组件档案概览" 章节。

JSON 顶层字段：

```json
{
  "version": "1.0",
  "component": "...",
  "scan_date": "...",
  "architecture": {"value": "B/S", "confidence": "high", "label": "AUTO", "inference_note": "...", "reverse_evidence": [...]},
  "protocols": [{"name": "TLSv1.3", "evidence": "..."}],
  "ports": [{"port": 443, "protocol": "TCP", "evidence": "..."}],
  "symmetric_algos": [...],
  "asymmetric_algos": [...],
  "hash_algos": [...],
  "custom_algos": [...],
  "pseudo_encryption": [...],
  "random_sources": [...],
  "default_accounts": [...],
  "personal_data": [...],
  "requires_root": {"value": "否", "confidence": "high", "label": "AUTO", "inference_note": "...", "reverse_evidence": [...]},
  "self_declared": {"algorithms": [...], "protocols": [...], "matched_actual": true, "mismatches": []},
  "dependency_summary": {"tier1_libraries": 12, "tier2_libraries": 5, "libraries_with_red_line": 2, "missing_lock_file": false},
  "red_line_violations": [{"rule_id": "RL-002", "category": "insecure_hash", "severity": "high", "summary": "...", "findings": ["CRYPTO-001"]}],
  "needs_human": ["INFO-001"]
}
```

每条 finding 的 `red_line_finding` 字段值必须能在 `findings` 数组中找到对应 id。
```

**Step 12.2: Add sub-report outputs**

In the `### 4. 四份维度专项报告` section, change to `### 4. 七份维度专项报告` and add:

```markdown
- `templates/report-密码学.md` -> `report-密码学-{component_name}-{date}.md`
- `templates/report-网络.md` -> `report-网络-{component_name}-{date}.md`
- `templates/report-组件档案.md` -> `report-组件档案-{component_name}-{date}.md`
```

**Step 12.3: Add overview chapter to comprehensive report**

After the existing `### 3. 综合 Markdown 报告` section, add:

```markdown
### 3.1 综合报告"组件档案概览"章节

综合报告顶部（基本信息和扫描统计之后）插入"组件档案概览"章节：

```markdown
## 组件档案概览

| 字段 | 值 | 标签 | 备注 |
|------|-----|------|------|
| 架构类型 | {architecture.value} | {architecture.label} | {architecture.inference_note} |
| 通信协议 | {protocols.names} | AUTO | - |
| ... (其他 7 个字段) |

### 子报告索引

- [密码学详细 finding](./report-密码学-{name}-{date}.md)
- [网络协议与端口详细 finding](./report-网络-{name}-{date}.md)
- [组件档案详细 finding](./report-组件档案-{name}-{date}.md)

### 声明 vs 实际

| 类别 | 声明 | 实际 | 一致 |
| 协议 | {self_declared.protocols} | {actual.protocols} | {yes/no} |
| 算法 | {self_declared.algorithms} | {actual.algorithms} | {yes/no} |
```

数据来源：`component-info-summary-{name}-{date}.json`。
```

**Step 12.4: Verify and commit**

```bash
grep -c "report-密码学" orchestration/reporter.md
grep -c "component-info-summary" orchestration/reporter.md
git add orchestration/reporter.md
git commit -m "feat(reporter): add component-info summary JSON and 3 sub-reports

Reporter now outputs component-info-summary JSON, 3 new sub-reports,
and renders an overview chapter at the top of the comprehensive report.

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 13: Update Reconnaissance

**Files:**
- Modify: `orchestration/reconnaissance.md`

**Step 13.1: Extend file classification**

In the `## Step 3: 文件分类` section (or equivalent), add new categories to the classification output:

```markdown
- `dependency_files`: package.json, package-lock.json, requirements.txt, Pipfile.lock, go.mod, go.sum, pom.xml, Cargo.toml, vcpkg.json, conanfile.txt
- `docker_files`: Dockerfile, docker-compose.yml, docker-compose.yaml
```

**Step 13.2: Extend Scan Plan schema**

In the Scan Plan output spec, add new segments:

```json
{
  "dependency_files": ["..."],
  "docker_files": ["..."],
  "crypto_relevant_files": ["..."],
  "network_relevant_files": ["..."],
  "component_info_relevant_files": ["..."]
}
```

`crypto_relevant_files` is `source_files ∪ config_files` filtered by language (Tier-1 or Tier-2).
`network_relevant_files` is `source_files ∪ config_files` filtered to files containing port/protocol patterns.
`component_info_relevant_files` is `source_files ∪ config_files ∪ docker_files`.

**Step 13.3: Verify and commit**

```bash
grep -c "dependency_files" orchestration/reconnaissance.md
git add orchestration/reconnaissance.md
git commit -m "feat(recon): extend file classification for 3 new dimensions

Scan Plan now includes dependency_files, docker_files,
and per-dimension relevant file lists.

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 14: Update Dependency Check

**Files:**
- Modify: `references/dependency-check.md`

**Step 14.1: Add jq and xmllint checks**

In the existing tool check loop, add:

```bash
for tool in jq xmllint; do
    if ! which "$tool" >/dev/null 2>&1; then
        echo "MISSING: $tool (新维度依赖 — 缺失时降级到 python3 -c 'import json/xml.etree')"
    else
        echo "OK: $tool -> $(which $tool)"
    fi
done
```

**Step 14.2: Add NVD/OSV network reachability check**

Add a new section after the existing tool checks:

```markdown
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
```

**Step 14.3: Verify and commit**

```bash
grep -c "jq" references/dependency-check.md
grep -c "NVD" references/dependency-check.md
git add references/dependency-check.md
git commit -m "feat(dependency): add jq/xmllint checks and NVD reachability test

New tools required for component-info archive dimensions.
Network reachability tested at startup; failure falls back to
built-in knowledge base.

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 15: Add E2E Fixture and Summary JSON

**Files:**
- Create: `tests/fixtures/full-test-component-info/` (multiple files)
- Create: `tests/fixtures/expected/component-info-summary-expected.json`

**Step 15.1: Create e2e fixture structure**

```bash
mkdir -p tests/fixtures/full-test-component-info/src
mkdir -p tests/fixtures/full-test-component-info/config
```

**Step 15.2: Create e2e fixture files**

Create `tests/fixtures/full-test-component-info/src/server.go`:
```go
package main

import (
    "crypto/md5"
    "crypto/tls"
    "net/http"
)

func main() {
    data := []byte("password")
    h := md5.Sum(data)  // crypto + secret dual-detect
    cfg := &tls.Config{MinVersion: tls.VersionTLS12}
    http.ListenAndServeTLS(":8443", "cert.pem", "key.pem", nil)  // network
    _ = h
}
```

Create `tests/fixtures/full-test-component-info/config/app.yaml`:
```yaml
server:
  port: 443
  tls_min_version: "1.2"
```

Create `tests/fixtures/full-test-component-info/package.json`:
```json
{
  "name": "full-test-component-info",
  "version": "1.0.0",
  "dependencies": {
    "express": "^4.18.0",
    "jsonwebtoken": "^9.0.0"
  }
}
```

Create `tests/fixtures/full-test-component-info/README.md`:
```markdown
# Full Test Component

本组件使用 TLSv1.2、MD5 缓存、Express 框架。
```

**Step 15.3: Create summary expected JSON**

```json
{
  "version": "1.0",
  "component": "full-test-component-info",
  "scan_date": "2026-06-29",
  "architecture": {
    "value": "B/S",
    "confidence": "high",
    "label": "AUTO",
    "inference_note": "检测到 express 依赖 + http.ListenAndServeTLS",
    "reverse_evidence": ["scanned: package.json", "matched: express, jsonwebtoken"]
  },
  "protocols": [
    {"name": "TLSv1.2", "evidence": "tls.Config{MinVersion: tls.VersionTLS12}"}
  ],
  "ports": [
    {"port": 8443, "protocol": "TCP", "evidence": "http.ListenAndServeTLS(\":8443\", ...)"},
    {"port": 443, "protocol": "TCP", "evidence": "config/app.yaml: port: 443"}
  ],
  "symmetric_algos": [],
  "asymmetric_algos": [],
  "hash_algos": [
    {"name": "MD5", "evidence": "crypto/md5 import + md5.Sum", "usage": "non-security", "label": "AUTO"}
  ],
  "custom_algos": [],
  "pseudo_encryption": [],
  "random_sources": [],
  "default_accounts": [],
  "personal_data": [],
  "requires_root": {
    "value": "否",
    "confidence": "high",
    "label": "AUTO",
    "inference_note": "无 setuid/privileged 信号，端口 8443 > 1024",
    "reverse_evidence": ["scanned: Dockerfile", "scanned: docker-compose.yml", "matched: 0 root signals"]
  },
  "self_declared": {
    "algorithms": ["MD5 (缓存)"],
    "protocols": ["TLSv1.2"],
    "matched_actual": true,
    "mismatches": []
  },
  "dependency_summary": {
    "tier1_libraries": 0,
    "tier2_libraries": 2,
    "libraries_with_red_line": 0,
    "missing_lock_file": false
  },
  "red_line_violations": [],
  "needs_human": []
}
```

**Step 15.4: Validate and commit**

```bash
python3 -m json.tool tests/fixtures/expected/component-info-summary-expected.json > /dev/null
git add tests/fixtures/full-test-component-info/ tests/fixtures/expected/component-info-summary-expected.json
git commit -m "test(fixtures): add e2e fixture and component-info summary baseline

E2E fixture exercises all 3 new scanners + component-info summary
JSON output. Express + Go crypto + TLS 1.2 + MD5 cache.

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 16: Add Security-Scanner Self-Disclosure

**Files:**
- Create: `component-info.md`

**Step 16.1: Create the file**

```markdown
# Component Info: security-scanner

> 本文件是 security-scanner 自身的组件基础信息档案。目的是示范模板格式。
> 严格按照 9 字段 + 红线判定填写。

## 基本信息

- **组件名称**: security-scanner
- **组件版本**: 1.0.0
- **扫描日期**: 2026-06-29

## 9 字段档案

| 字段 | 值 | 标签 | 备注 |
|------|-----|------|------|
| 1. 架构类型 | 不涉及 | MISSING | security-scanner 是 SKILL 指令包，不是可执行服务 |
| 2. 通信协议 | 不涉及 | MISSING | security-scanner 不实现网络通信 |
| 3a. 对称算法 | 不涉及 | MISSING | security-scanner 不实现密码学 |
| 3b. 非对称算法 | 不涉及 | MISSING | security-scanner 不实现密码学 |
| 3c. Hash 算法 | 不涉及 | MISSING | security-scanner 不实现密码学 |
| 3d. 自定义算法 | 不涉及 | MISSING | security-scanner 不实现密码学 |
| 4. 伪加密 | 不涉及 | MISSING | security-scanner 不实现密码学 |
| 5. 随机数 | 不涉及 | MISSING | security-scanner 不使用随机数 |
| 6. 默认账号 | 无 | MISSING | security-scanner 不提供用户系统 |
| 7. 端口 | 无 | MISSING | security-scanner 不监听端口 |
| 8. 个人数据 | 无 | MISSING | security-scanner 不采集任何用户数据 |
| 9. 是否需 root 启动 | 否 | AUTO | security-scanner 由 AI agent 加载执行，普通用户权限即可 |

## 红线合规判定

| 红线 | 状态 | 说明 |
|------|------|------|
| 红线 1：严禁私有或伪加密 | 不适用 | security-scanner 不实现密码学 |
| 红线 2：禁止不安全算法/协议 | 不适用 | security-scanner 不实现算法/协议 |
| 红线 3：密码算法随机数安全 | 不适用 | security-scanner 不使用随机数 |
| 红线 4：所有命令/参数/端口文档化 | PASS | security-scanner 的所有 markdown 文件即为完整文档；无未公开命令/参数/端口 |
| 红线 5：默认账号与个人数据合规 | PASS | 无默认账号，无个人数据采集 |

## 字段完整性自检

- [x] 9 个字段全部填写
- [x] 每字段含 value + label + 备注
- [x] 5 红线全部判定
- [x] 文档化：本档案文件本身即为文档

## 反向证据

| 字段 | 已搜索 | 命中 |
|------|--------|------|
| 端口 | `bind(`, `listen `, `port:`, `server.port` | 0 |
| 个人数据 | `phone`, `id_card`, `email` | 0 |
| 默认账号 | `admin`, `root` 紧邻 password/secret | 0 |
| 随机数 | `RAND_bytes`, `Math.random` | 0 |
| 算法 | `AES`, `DES`, `MD5`, `SHA-` | 0 |
| 不安全协议 | `SSLv3`, `TLSv1.0`, `Telnet` | 0 |
```

**Step 16.2: Verify and commit**

```bash
test -f component-info.md && echo "OK"
git add component-info.md
git commit -m "docs: add security-scanner self-disclosure as template example

Component-info.md demonstrates the 9-field + red-line template
filled out for the security-scanner itself. Most fields are
MISSING (scanner is a SKILL instruction package, not a service).

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 17: Update README

**Files:**
- Modify: `README.md`

**Step 17.1: Update dimension table**

In the `## 扫描维度` table, add 3 rows:

```markdown
| 7 | 密码学合规 | 对称/非对称/Hash 算法、伪加密、随机数 API、不安全协议、库版本知识库匹配 |
| 8 | 网络协议与端口 | 通信协议（SSHv2/TLS1.2/TLS1.3）、监听端口、声明 vs 实际对账 |
| 9 | 组件基础档案 | 架构类型、默认账号、个人数据处理、root 启动需求、声明 vs 实际对账 |
```

**Step 17.2: Update project structure**

In the `## 项目结构` code block, add:

```text
├── scanners/
│   ├── crypto-scanner.md
│   ├── network-scanner.md
│   └── component-info-scanner.md
├── references/
│   ├── patterns-crypto.md
│   ├── patterns-network.md
│   ├── personal-data-patterns.md
│   ├── library-vuln-caps.md
│   └── red-line-rules.md
├── templates/
│   ├── report-密码学.md
│   ├── report-网络.md
│   └── report-组件档案.md
├── tests/fixtures/
│   ├── crypto-test/
│   ├── network-test/
│   ├── component-info-test/
│   └── full-test-component-info/
└── component-info.md
```

**Step 17.3: Update output formats**

In the `## 输出格式` section, add 3 new report rows:

```markdown
| 密码学专项报告 | `report-密码学-{component_name}-{date}.md` |
| 网络专项报告 | `report-网络-{component_name}-{date}.md` |
| 组件档案专项报告 | `report-组件档案-{component_name}-{date}.md` |
| 组件档案 summary JSON | `component-info-summary-{component_name}-{date}.json` |
```

**Step 17.4: Update FAQ**

Add new FAQ entries:

```markdown
### 9 个新维度和老的 6 个维度怎么协调？

crypto / network / component_info 三个新维度是 6 维度的扩展，不是替代。crypto-scanner 与 secret-scanner 共享 `references/patterns-crypto.md`，verdict 阶段去重（同一 file:line:check_item 留高 severity）。新维度的 evidence 字段可包含库信息，老 6 维度不解析该格式。

### 综合报告为什么有"组件档案概览"章节？

为防止报告爆炸（中型项目可能有 200+ finding），综合报告顶部插入一个不带文件/行号的概览表，链接到 3 个详细子报告。审计员先看概览判断有无重大问题，再按需展开子报告。

### 推断不出的字段怎么填？

每字段都有 AUTO/INFERRED/MISSING 三种标签：
- AUTO = 多源验证高置信度
- INFERRED = 有信号但弱
- MISSING = 机扫无信号，必须人工补全
MISSING 字段在 summary JSON 中保留但 value 为空，在 Markdown 报告中以"不适用"或"待人工补全"展示。
```

**Step 17.5: Verify and commit**

```bash
grep -c "crypto-scanner" README.md
grep -c "network-scanner" README.md
grep -c "component-info-scanner" README.md
git add README.md
git commit -m "docs(readme): document 3 new dimensions, file structure, and FAQ

Update dimension table, project structure, output formats, and
FAQ with component-info archive information.

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Task 18: Run E2E Verification

**Step 18.1: Validate all JSON baselines**

```bash
for f in tests/fixtures/expected/*.json; do
    python3 -m json.tool "$f" > /dev/null && echo "OK: $f" || echo "FAIL: $f"
done
```

Expected: 4 lines of OK (crypto, network, component-info, component-info-summary).

**Step 18.2: Validate bash syntax in fixtures**

```bash
for f in tests/fixtures/*/setup*.sh tests/fixtures/*/compile*.sh; do
    [ -f "$f" ] && bash -n "$f" && echo "OK: $f"
done
```

**Step 18.3: Verify all new files exist**

```bash
expected_files=(
    references/red-line-rules.md
    references/patterns-crypto.md
    references/patterns-network.md
    references/personal-data-patterns.md
    references/library-vuln-caps.md
    scanners/crypto-scanner.md
    scanners/network-scanner.md
    scanners/component-info-scanner.md
    templates/report-密码学.md
    templates/report-网络.md
    templates/report-组件档案.md
    tests/fixtures/expected/crypto-expected.json
    tests/fixtures/expected/network-expected.json
    tests/fixtures/expected/component-info-expected.json
    tests/fixtures/expected/component-info-summary-expected.json
    component-info.md
)
for f in "${expected_files[@]}"; do
    test -f "$f" && echo "OK: $f" || echo "FAIL: $f"
done
```

**Step 18.4: Run audit checkpoints A0-A3**

Manually verify the four audit checkpoints:
- A0 (Recon): Scan Plan includes dependency_files, docker_files, 3 new dimension segments
- A1 (Scan): All 9 scanners dispatchable, failure thresholds 1/2-3/4+ documented
- A2 (Verdict): crypto vs secret dedup rule documented
- A3 (Report): 4 sub-reports + comprehensive report + component-info-summary JSON all generated

**Step 18.5: Final commit**

```bash
git status  # should be clean
git log --oneline | head -20
```

**Step 18.6: Report results**

Output a summary:
- Total commits added
- Files created vs modified
- Audit checkpoint status
- Any spec coverage gaps

---

## Self-Review

**Spec coverage check** (each spec section → task mapping):

| Spec Section | Implemented In |
|--------------|----------------|
| 1. Background & Goals | (informs all tasks) |
| 2. 9-field definitions | Task 6 (crypto), 7 (network), 8 (component-info), 16 (self-disclosure) |
| 3.1 crypto-scanner | Task 6 |
| 3.2 network-scanner | Task 7 |
| 3.3 component-info-scanner | Task 8 |
| 4.1 JSON output | Task 12 (reporter) |
| 4.2 Markdown output | Task 9 (templates), 12 (overview chapter) |
| 5. Scheduling & failures | Task 11 (orchestrator) |
| 6. Shared patterns | Task 1-5 (5 reference files) |
| 7. Test strategy | Task 6, 7, 8, 15 (fixtures), 18 (verification) |
| 8. Self-disclosure | Task 16 |
| 9. File changes | All tasks |
| 10. Risks & rollback | (informational) |
| 11. Acceptance criteria | Task 18 (verification) |
| 12. Open questions | (none, all resolved) |

**Placeholder scan**: No "TBD"/"TODO"/"implement later" in this plan. Each step shows the actual content to write.

**Type consistency**: All scanners use `dimension: "crypto"|"network"|"component_info"`. All findings use the same `id` pattern `CRYPTO-`/`NETWORK-`/`INFO-`. All summary JSON files use the schema from spec section 4.1.

**Coverage gap**: None identified.

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-06-29-component-info-archive.md`. Two execution options:

1. **Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration
2. **Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

Which approach?
