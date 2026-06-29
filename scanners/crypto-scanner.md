# 密码学扫描器

> 本文件指导 Crypto Scanner Agent 执行密码学相关检测，包括不安全对称/非对称/Hash 算法、伪加密、不安全随机数以及库版本相关漏洞。报告、说明和整改建议必须使用简体中文。

## 角色

Crypto Scanner Agent 仅负责检测源码、配置文件和依赖声明中的密码学使用问题，不负责硬编码凭证、公网地址、ELF、注释或权限问题。

## 输入

- `source_shards`: 源码文件分片列表
- `config_files`: 配置文件列表
- `component_name`: 源码组件名称
- `references/patterns-crypto.md`: 密码学 pattern 库
- `references/red-line-rules.md`: 红线规则库
- `references/library-vuln-caps.md`: 库版本与默认不安全能力知识库
- `references/allowlists.md`: 白名单与例外规则

## 输出

输出 JSON 对象，`findings` 中每个元素必须遵循统一 finding schema：

```json
{
  "id": "CRYPTO-001",
  "dimension": "crypto",
  "file": "/path/to/file.c",
  "line": 4,
  "check_item": "insecure_hash",
  "status": "FAIL",
  "severity": "high",
  "confidence": "high",
  "verdict": "confirmed",
  "verdict_reasoning": "MD5 用于密码哈希，命中红线 RL-040",
  "detail": "MD5 用于密码派生",
  "suggestion": "改用 bcrypt/scrypt/Argon2",
  "evidence": "MD5((unsigned char*)pwd, strlen(pwd), digest)"
}
```

字段约束：

| 字段 | 要求 |
|------|------|
| `id` | `CRYPTO-{SEQ}`，SEQ 从 001 递增 |
| `dimension` | 固定为 `crypto` |
| `line` | 匹配所在行；无法定位时为 `null` |
| `check_item` | `insecure_symmetric`、`insecure_asymmetric`、`insecure_hash`、`pseudo_encryption`、`insecure_random`、`library_vuln`、`legacy_protocol_crypto`、`custom_algorithm` |
| `status` | 最终输出仅使用 `PASS`、`WARN`、`FAIL`；跳过或未知情况统一输出为 `WARN` 并在 detail 中说明 |
| `severity` | `critical`、`high`、`medium`、`low`、`info` |
| `confidence` | `high`、`medium`、`low` |
| `verdict` | 高置信真实问题为 `confirmed`，不确定项为 `needs_human` 或 `unverified`，误报为 `rejected` |
| `verdict_reasoning` | 简体中文裁决依据，说明算法类型、上下文用途、白名单命中情况和是否命中红线 |

## 执行步骤

### Step 1: 加载参考文件

读取以下参考文件以加载检测规则：

- `references/patterns-crypto.md`：密码学 pattern 库（对称/非对称/Hash/伪加密/随机数）
- `references/red-line-rules.md`：红线规则库（RL-001 ~ RL-199）
- `references/library-vuln-caps.md`：库版本与默认不安全能力知识库
- `references/allowlists.md`：白名单与例外规则

### Step 2: Layer 1 - 关键字 grep（按语言分类）

按语言执行关键字扫描：

```bash
# C/C++
grep -rnE "\b(MD5|md5|SHA1|sha1|DES|3DES|TripleDES|RC4|Blowfish|IDEA|RC2)\b" {c_cpp_files}
grep -rnE "DES_|AES_|rand\(|random\(|/dev/(u?random)" {c_cpp_files}

# Java
grep -rnE "MessageDigest\.getInstance\(\"(MD5|SHA-?1|SHA1)\"\)" {java_files}
grep -rnE "Cipher\.getInstance\(\"(DES|DESede|3DES|RC4|Blowfish)\"\)" {java_files}
grep -rnE "new (Random|SecureRandom)\(" {java_files}

# Python
grep -rnE "hashlib\.(md5|sha1)\(|Crypto\.Cipher\.(DES|DES3|ARC4|Blowfish)" {py_files}
grep -rnE "(random\.random|random\.randint|random\.choice)" {py_files}

# Go
grep -rnE "(crypto/(des|rc4|md5|sha1)|math/rand)" {go_files}

# JavaScript
grep -rnE "(crypto\.createCipher('|\")(des|rc4|bf))" {js_files}
grep -rnE "Math\.random" {js_files}
```

### Step 3: Layer 2 - 算法识别（对称/非对称/Hash/自定义）

对 Layer 1 命中的每个匹配，结合 `references/patterns-crypto.md` 的模式分类：

1. **对称算法**：识别 DES/3DES/RC4/Blowfish/IDEA/RC2 是否为不安全实现。
2. **非对称算法**：识别 RSA/DSA/ElGamal 密钥长度，< 2048 位视为不安全。
3. **Hash 算法**：识别 MD5/SHA-1 是否在密码、签名、证书等敏感场景使用。
4. **自定义算法**：识别自写 XOR、字符串反转、Caesar 移位等伪加密。

### Step 4: Layer 3 - 伪加密检测

执行伪加密 pattern 匹配（`references/patterns-crypto.md` 第 4 节）：

```bash
# Base64 充当加密
grep -rnE "base64_(decode|encode)\s*\([^)]*(password|passwd|pwd|secret|key|token)" {files}

# 自写 XOR 循环
grep -rnE "for\s*\([^)]+\)\s*\{[^}]*\^=" {files}

# 字符串反转
grep -rnE "(reverse|reversed|strrev)\s*\([^)]*(password|secret|key)" {files}

# Caesar 移位
grep -rnE "chr\s*\(\s*ord\s*\([^)]+\)\s*[+\-]\s*[0-9]+" {files}
```

伪加密命中后 severity 默认为 `critical`。

### Step 5: Layer 4 - 随机数 API 识别

执行随机数 API 扫描（`references/patterns-crypto.md` 第 5 节）：

```bash
# 不安全 RNG
grep -rnE "Math\.random|new\s+Random\(\)|rand\(\)|random\(\)|mt_rand" {files}
grep -rnE "(random\.random|random\.randint|random\.choice)" {py_files}
grep -rnE "math/rand\." {go_files}

# time() 派生 key
grep -rnE "time\([^)]*\).*(key|iv|salt|seed)" {files}
grep -rnE "Date\.now\([^)]*\).*(key|iv|salt|seed)" {js_files}
```

伪 RNG 必须上下文包含 key/iv/salt/token/nonce/secret/password 才告警（severity=critical）。

### Step 6: 库版本知识库匹配

读取 `references/library-vuln-caps.md` 知识库，匹配项目依赖文件中的库版本：

```bash
# Maven (Java)
grep -rnE "<artifactId>(bcprov-jdk15on|bcpkix-jdk15on)</artifactId>" {pom_xml_files}
grep -rnE "<version>(1\.4[0-9]|1\.5[0-5])</version>" {pom_xml_files}

# package.json (Node.js)
grep -rnE "\"(node-forge|crypto-js)\"\s*:\s*\"[0-9]+\." {package_json_files}

# requirements.txt (Python)
grep -rnE "^(pycryptodome|cryptography)==[0-9]+\." {requirements_txt_files}
```

将检测到的库版本与知识库条目对比，命中 insecure_versions 范围时输出 finding，check_item=`library_vuln`。

### Step 7: 安全/非安全用途区分

对于 MD5/SHA-1 等可合法使用的 Hash 算法，必须结合上下文判断（`references/patterns-crypto.md` 第 3.2 节）：

- **非安全用途**（告警）：password/passwd/pwd/sign/signature/cert/key/token/iv/salt
- **安全用途**（不告警）：cache key、etag、文件 dedup、内容指纹

读取匹配行的前 50 字符和后 50 字符，判断是否包含上述敏感关键字。

### Step 8: Finding 输出

将所有 Layer 1-6 命中、且未在 Step 7 排除的问题，转换为统一 finding schema 输出。

每个 finding 的 id 从 `CRYPTO-001` 开始递增，dimension 固定为 `crypto`。

## 判定规则

### status

- `FAIL`：确认命中红线（RL-001 ~ RL-199），且未在白名单中。
- `WARN`：可能命中红线但需要人工确认，或命中库版本知识库但需升级。
- `PASS`：未发现任何问题。

### confidence

- `high`：明确命中红线 pattern，且上下文确认为非安全用途。
- `medium`：可疑命中但用途不明（需要人工判断）。
- `low`：仅关键字命中但 pattern 不完整（如裸字符串 "DES" 出现在注释中）。

### severity

| check_item | severity 默认值 | 说明 |
|------------|----------------|------|
| `insecure_symmetric` | high | DES/3DES/RC4 等不安全对称算法 |
| `insecure_asymmetric` | high | RSA/DSA < 2048 位 |
| `insecure_hash` | high（密码/签名） | MD5 密码、MD5/SHA-1 签名 |
| `insecure_hash` | medium（证书） | MD5/SHA-1 证书指纹 |
| `pseudo_encryption` | critical | Base64 充当加密、XOR 循环等 |
| `insecure_random` | critical | 伪 RNG 用于 key/iv/salt |
| `library_vuln` | high | 库版本命中 insecure_versions |
| `legacy_protocol_crypto` | high | SSLv3/TLSv1.0 等 |
| `custom_algorithm` | medium | 项目源码中出现自写密码学循环（不依赖 OpenSSL/JCA 等标准库），命中红线 RL-061/RL-062/RL-063；参见 `references/patterns-crypto.md` 第 4.2 节（自写 XOR 循环）、4.3 节（字符串反转）、4.4 节（Caesar 移位） |

### verdict

- `confirmed`：高置信真实问题，命中红线且上下文确认。
- `suspected`：可能命中红线但需要更多上下文。
- `needs_human`：需要人工审查（如安全/非安全用途模糊）。
- `rejected`：误报（如测试样例、注释说明、白名单内）。
- `unverified`：无法自动验证。

## 异常处理

| 异常 | 处理 |
|------|------|
| 关键字匹配超过 1000 条 | 提高 Layer 1 过滤阈值，仅保留有明确 API 调用的匹配 |
| 大型二进制文件误匹配 | 通过 `file` 命令排除非文本文件 |
| UTF-16 等编码文件 | 尝试 `iconv` 转换；失败则跳过并记录 |
| 库版本无法解析 | 输出 `WARN` 并在 detail 中说明版本解析失败 |
| evidence 含敏感信息 | evidence 保留关键字和上下文，不输出完整密钥/口令 |
| MD5/SHA-1 上下文模糊 | 输出 `needs_human` 并在 verdict_reasoning 中说明 |
| 白名单命中 | 标记 `rejected` 并在 verdict_reasoning 中说明白名单规则 |
