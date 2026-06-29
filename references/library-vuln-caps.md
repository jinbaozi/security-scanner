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
