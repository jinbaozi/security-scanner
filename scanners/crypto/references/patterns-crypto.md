# 密码学 Patterns 库

> 本文件集中维护 crypto scanner 专属的密码学相关 pattern 集合。
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
| SKIPJACK | `\bSKIPJACK\|skipjack_encrypt\|skipjack_set_key` | high |
| AES-ECB | `AES/ECB\|EVP_aes_.*_ecb\|MODE_ECB` | high |

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
| DH 512 位参数 | `DH_generate_parameters_ex\([^,]+,\s*512\|dhparam\s+512\|ffdhe512` | high |
| DH 1024 位参数 | `DH_generate_parameters_ex\([^,]+,\s*1024\|dhparam\s+1024\|ffdhe1024` | high |

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
| MD2 | `\bMD2\b\|md2\(` | 任意密码学用途 | 无 |
| MD4 | `\bMD4\b\|md4\(` | 任意密码学用途 | NTLM 兼容场景需人工确认 |
| HMAC-*-96 | `HMAC-?(?:MD5\|SHA1\|SHA256)-?96\|hmac.*truncate.*96` | 认证码截断且无协议证明 | 标准协议中经评估的截断长度 |

安全/非安全用途通过上下文关键字判断（前 50 字符或后 50 字符是否包含 password/passwd/pwd/sign/signature/cert/key/token/iv/salt 等关键字）。SHA-1 在签名、证书、完整性保护和认证用途为 FAIL；在 HMAC 兼容协议中默认 WARN-PASS 并要求人工确认协议约束；在 Git hash、内容指纹、缓存 key 等非安全用途不告警。

### 3.3 推荐国密算法（INFO）

| 算法 | Pattern | 说明 |
|------|---------|------|
| SM4 | `\bSM4\|sm4_crypt\|sms4` | 国密对称算法推荐项，作为 INFO 记录，不作为 FAIL |
| SM2 | `\bSM2\|sm2_` | 国密非对称算法推荐项，作为 INFO 记录，不作为 FAIL |
| SM3 | `\bSM3\|sm3_` | 国密 Hash 推荐项，作为 INFO 记录，不作为 FAIL |

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
| Python `os.urandom` | `os\.urandom\|secrets\.\|SystemRandom` |
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
