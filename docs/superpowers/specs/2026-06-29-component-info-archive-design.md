# 组件基础信息档案 (Component Info Archive) — 设计

**日期**：2026-06-29
**状态**：待用户复核
**目的**：在 `security-scanner` 中新增 3 条扫描维度，自动生成目标项目的"组件基础信息档案"，覆盖 9 字段 + 红线合规判定。

---

## 1. 背景与目标

### 1.1 业务背景

`security-scanner` 当前覆盖 6 个维度的安全合规扫描：ELF 安全编译、公网地址、口令硬编码、未公开接口、敏感文件泄露、文件权限。这些维度回答了"代码里有什么安全风险"，但没有回答"这个组件本身长什么样"。

需要新增的"组件基础信息档案"回答的是基础信息盘点问题：组件用什么算法、走什么协议、开哪些端口、默认账号是什么、采集哪些个人数据、是否要 root 启动。该信息是开展安全检查、风险评估和合规审计的基础数据。

### 1.2 红线要求（来自需求方）

| # | 红线 | 检查维度归属 |
|---|------|-------------|
| 1 | 严禁私有或伪加密算法（如 Base64 充当加密） | crypto |
| 2 | 禁止默认启用不安全算法/协议（MD5/DES/3DES/RC4/Telnet/SSL3.0/RSA1024 等） | crypto + network |
| 3 | 密码算法随机数必须用安全 RNG（`/dev/urandom`、`RAND_bytes`、`SecureRandom`） | crypto |
| 4 | 所有命令/参数/端口必须文档化 | network + comment（已有） |
| 5 | 默认账号与个人数据必须如实披露 | component_info |

### 1.3 设计目标

- 9 字段全部能机扫或推断，不能推断的字段明确标 `MISSING` 并提示人工补全
- 红线违规自动标 `FAIL` 并给出修复建议
- 双产出（JSON + Markdown），与现有 reporter 工作流一致
- 报告爆炸（200+ finding）下仍可读
- 现有 6 维度 schema 不破坏，新功能加新文件

### 1.4 非目标

- 不替代人工合规审计；高风险红线违规最终仍需 `needs_human` 复核
- 不主动连接目标系统的运行实例（端口扫描、API 探测等）
- 不做依赖库的 CVE 全量比对（仅与内置 `library-vuln-caps.md` 知识库做匹配）
- 不改 comment-scanner（已覆盖红线 #4 未公开接口）

---

## 2. 9 字段定义

| # | 字段名 | 字段类型 | 维度归属 | 可机扫 | 反向证据 |
|---|--------|---------|---------|--------|---------|
| 1 | 架构类型 | enum(`B/S`、`C/S`、`不涉及`、`MISSING`) | component_info | 推断 | 已搜索 `import.*Django`、`include.*Qt` 等 |
| 2 | 通信协议 | enum(`SSHv2`、`TLS1.2`、`TLS1.3`、`SSL3.0`、`Telnet`、...) | network | 直接枚举 | 已 grep `ssh|tls|ssl|telnet` |
| 3 | 算法（4 类） | list（对称/非对称/Hash/自定义） | crypto | 直接枚举 | 已 grep 算法关键字 |
| 4 | 伪加密 | list(`Base64充当密码`、自写 XOR、字符串反转) | crypto | 启发式 | 已搜索 `base64.*password` |
| 5 | 随机数生成方式 | list(`/dev/urandom`、`RAND_bytes`、`SecureRandom`、`Math.random`、`java.util.Random`、`time()` 派生) | crypto | 直接枚举 | 已 grep 上述 API |
| 6 | 默认账号 | list(admin、root、user、...) | component_info | 启发式 | 已搜索硬编码凭证 |
| 7 | 端口 | list(80、443、8080、...) | network | 直接枚举 | 已 grep `bind(|listen |port:` |
| 8 | 个人数据 | list(姓名、手机号、身份证、邮箱、位置、设备标识) | component_info | 字段名正则 + 加密/脱敏检查 | 已搜索字段名 |
| 3a | 对称算法 | list(AES、SM4、DES、3DES、RC4、Blowfish、IDEA) | crypto | 直接枚举 | 已 grep 算法关键字 |
| 3b | 非对称算法 | list(RSA、ECC、SM2、DSA、ElGamal) | crypto | 直接枚举 | 已 grep 算法关键字 |
| 3c | Hash 算法 | list(MD5、SHA-1、SHA-256、SHA-512、SHA3、SM3、BLAKE2) | crypto | 直接枚举 | 已 grep 算法关键字 |
| 3d | 自定义算法 | list(项目自写密码学循环) | crypto | 启发式 | 已搜索自写加密模式 |
| 9 | 是否需 root 启动 | enum(`是`/`否`) + reason | component_info | 多源交集 | 已搜索 `setuid|cap_setuid|privileged: true` |

每字段输出 schema：

```json
{
  "value": "B/S",
  "confidence": "high|medium|low",
  "label": "AUTO|INFERRED|MISSING",
  "inference_note": "检测到 Django 4.2 + DRF + 前端 React 项目目录",
  "reverse_evidence": ["scanned: 22 个 web framework 导入", "matched: Django, DRF, FastAPI"]
}
```

---

## 3. 三条新扫描维度

### 3.1 crypto-scanner

**职责**：枚举算法、伪加密判定、随机数 API 识别、不安全协议识别。

**输入**：`source_shards + config_files`

**输出维度**：`dimension: "crypto"`

**finding schema 沿用主 schema**：

```json
{
  "id": "CRYPTO-001",
  "dimension": "crypto",
  "file": "/path/to/file.c",
  "line": 42,
  "check_item": "insecure_hash",
  "status": "FAIL",
  "severity": "high",
  "confidence": "high",
  "verdict": "confirmed",
  "verdict_reasoning": "...",
  "detail": "检测到 MD5 用于密码哈希",
  "suggestion": "改用 bcrypt/scrypt/Argon2",
  "evidence": "library=OpenSSL@1.0.1g | library_version=1.0.1g | trigger=MD5 password hash | line=42: md5(pwd)"
}
```

**红线判定**：

| check_item | 触发 pattern | severity | 红线 |
|------------|-------------|---------|------|
| `insecure_symmetric` | 命中 `DES`、`3DES`、`RC4` | high | 红线 2 |
| `pseudo_encryption` | `base64_decode.*password\|secret\|key`、自写 XOR 字符串 | critical | 红线 1 |
| `insecure_asymmetric` | 命中 `RSA<2048`、`DSA<2048`、`ElGamal` | high | 红线 2 |
| `insecure_hash` | MD5 用于 `password\|passwd\|pwd`、SHA-1 用于 `signature\|sign\|cert` | high | 红线 2 |
| `insecure_random` | `Math.random`、`java.util.Random`、`rand()` 用于 `key\|iv\|salt\|token\|nonce` | critical | 红线 3 |
| `legacy_protocol_crypto` | `SSLv3`、`SSLv2`、`TLSv1.0`、`TLSv1.1` | high | 红线 2 |
| `custom_algorithm` | 项目源码中出现自写密码学循环（不依赖 OpenSSL/JCA 等标准库） | medium | 红线 1 |

**安全/非安全用途区分**（默认区分，可降级）：

| Hash 算法 | 安全用途（告警） | 非安全用途（不告警） |
|----------|----------------|-------------------|
| MD5 | 密码哈希、token 派生、签名、证书指纹 | cache key、etag、文件 dedup、内容指纹 |
| SHA-1 | 数字签名、证书 | git commit hash、内容指纹 |

**安全 RNG vs 伪 RNG**：

| 安全 RNG（不告警） | 伪 RNG（红线告警） |
|------------------|-----------------|
| `/dev/urandom`、`/dev/random` | `Math.random`（JS） |
| OpenSSL `RAND_bytes`、`RAND_priv_bytes` | `java.util.Random`（非 SecureRandom） |
| JDK `java.security.SecureRandom` | `rand()`（C） |
| 类 Unix `/dev/urandom` 文件读取 | `time()` 派生 key |
| iPSI `CRYPT_random`、VPP `IPSI_CRYPT_rand_bytes` | `mt_rand()`（PHP） |
| TEE `TEE_GenerateRandom` | `os.urandom`（Python 实际安全，但语义弱） |

### 3.2 network-scanner

**职责**：枚举通信协议、监听端口。

**输入**：`source_shards + config_files`

**输出维度**：`dimension: "network"`

**红线判定**：

| check_item | 触发 pattern | severity |
|------------|-------------|---------|
| `legacy_protocol` | `SSLv3`、`SSLv2`、`TLSv1.0`、`TLSv1.1`、`Telnet`、`HTTP`（敏感字段） | high |
| `undocumented_port` | bind/listen 的端口未在 `README.md`/`docs/`/`*.conf` 注释中提及 | medium |
| `default_protocol_insecure` | 默认配置走 HTTP/HTTPS 但握手协议版本可降级到 SSL3.0/TLS1.0 | high |

**端口识别 pattern**（跨语言）：

| 语言/格式 | pattern |
|----------|---------|
| C/C++ | `bind(`, `listen(` |
| Go | `net.Listen(`, `http.ListenAndServe(` |
| Python | `socket.bind(`, `app.run(`, `uvicorn.run(` |
| Java | `new ServerSocket(`, `server.port=` |
| JavaScript/Node | `app.listen(`, `server.listen(` |
| 配置 | YAML/JSON/Properties 中 `port:`, `listen:`, `server.port` |
| 文档 | `README.md`、`*.md` 中提到端口号 |

### 3.3 component-info-scanner

**职责**：架构类型推断、默认账号识别、个人数据采集检查、root 启动需求识别。

**输入**：`source_shards + config_files + docker_files`

**输出维度**：`dimension: "component_info"`

**架构类型推断**：

| 信号 | 推断 |
|------|------|
| Web framework 库（Django/Flask/Express/Spring/Tomcat/FastAPI/...） | B/S |
| GUI 库（Qt/GTK/Swing/JavaFX/Electron/...） | C/S |
| 同时有 web framework 和 GUI | B/S（带 C 端） |
| 都没有 | MISSING（提示人工补全） |

**默认账号识别**：

| pattern | severity | 红线 |
|---------|---------|------|
| 硬编码 `admin/123456`、`root/root`、`user/user` | high | 红线 5 |
| 数据库 init 脚本含默认账号且无强制改密提示 | high | 红线 5 |
| README 中提到"默认账号 admin"且无"首次登录修改密码"流程 | medium | 红线 5 |

**个人数据处理**：

| 类别 | 字段名正则 | 用途 |
|------|----------|------|
| 姓名 | `name`, `username`, `real_name`, `full_name` | 用户标识 |
| 手机号 | `phone`, `mobile`, `tel`, `cellphone` | 联系方式 |
| 身份证 | `id_card`, `idcard`, `identity`, `id_number` | 实名 |
| 邮箱 | `email`, `mail` | 联系方式 |
| 位置 | `location`, `gps`, `latitude`, `longitude`, `address` | 位置服务 |
| 设备标识 | `device_id`, `imei`, `mac`, `udid`, `android_id` | 设备追踪 |

红线检查（命中即报）：

- 身份证/手机号/银行卡字段明文存储（无 `encrypt\|hash\|mask`）
- 上述字段通过 HTTP（非 HTTPS）传输
- 上述字段出现在日志/JSON dump 中且无脱敏

**root 启动需求**（多源交集 → AUTO；单源 → INFERRED）：

| 信号 | 权重 |
|------|------|
| 源码中 `setuid(0)`、`seteuid(0)`、`cap_setuid` syscall | 强 |
| 二进制 setuid 位（`u+s`） | 强 |
| `docker-compose.yml`/`Dockerfile` 含 `privileged: true` 或 `cap_add: SYS_ADMIN` | 强 |
| 系统服务 unit 文件含 `User=root` 且无 sandbox 配置 | 强 |
| 端口 < 1024 且无 capability 配置 | 弱 |

---

## 4. 双产出与报告结构

### 4.1 JSON 产出

**主 finding JSON**（沿用现有 schema）：

```json
{
  "version": "1.0",
  "component": "...",
  "scan_date": "2026-06-29",
  "findings": [
    {"id": "CRYPTO-001", "dimension": "crypto", "file": "...", ...},
    {"id": "NETWORK-001", "dimension": "network", "file": "...", ...},
    {"id": "INFO-001", "dimension": "component_info", "file": "...", ...}
  ]
}
```

**组件档案 summary JSON**（新结构）：

```json
{
  "version": "1.0",
  "component": "...",
  "version": "...",
  "scan_date": "2026-06-29",
  "architecture": {"value": "B/S", "confidence": "high", "label": "AUTO", "inference_note": "...", "reverse_evidence": [...]},
  "protocols": [{"name": "TLSv1.3", "evidence": "..."}, {"name": "TLSv1.2", "evidence": "..."}],
  "ports": [{"port": 443, "protocol": "TCP", "evidence": "..."}, {"port": 80, "protocol": "TCP", "evidence": "..."}],
  "symmetric_algos": [...],
  "asymmetric_algos": [...],
  "hash_algos": [...],
  "custom_algos": [],
  "pseudo_encryption": [],
  "random_sources": [{"api": "RAND_bytes", "evidence": "src/foo.c:12"}, {"api": "Math.random", "evidence": "src/bar.js:34", "red_line_finding": "CRYPTO-005"}],
  "default_accounts": [...],
  "personal_data": [{"field": "phone", "category": "phone", "storage": "plaintext", "red_line_finding": "INFO-007"}],
  "requires_root": {"value": "否", "confidence": "high", "label": "AUTO", "inference_note": "...", "reverse_evidence": [...]},
  "self_declared": {
    "algorithms": ["SM4", "SM2", "SM3"],
    "protocols": ["TLSv1.3"],
    "matched_actual": true,
    "mismatches": []
  },
  "dependency_summary": {
    "tier1_libraries": 12,
    "tier2_libraries": 5,
    "libraries_with_red_line": 2,
    "missing_lock_file": false
  },
  "red_line_violations": [
    {"rule_id": "RL-002", "category": "insecure_hash", "severity": "high", "summary": "MD5 用于密码哈希", "findings": ["CRYPTO-001", "CRYPTO-002"]}
  ],
  "needs_human": ["PERSONAL_DATA-001"]
}
```

### 4.2 Markdown 产出

| 文件 | 内容 | 体积预期 |
|------|------|---------|
| `security-scan-report-{name}-{date}.md` | 综合报告，顶部 1 个"组件档案概览"章节（无文件/行号） + 9 字段总览表 + 三个子报告的相对路径 | 中（< 200 行） |
| `report-密码学-{name}-{date}.md` | crypto-scanner 全部 finding | 可能大（> 500 行） |
| `report-网络-{name}-{date}.md` | network-scanner 全部 finding | 中 |
| `report-组件档案-{name}-{date}.md` | component-info-scanner 全部 finding + 9 字段完整表 + 声明 vs 实际对账表 + 红线汇总 | 中 |

**综合报告"组件档案概览"章节示例**：

```markdown
## 组件档案概览

| 字段 | 值 | 标签 | 备注 |
|------|-----|------|------|
| 架构类型 | B/S | AUTO | Django 4.2 + React |
| 通信协议 | TLSv1.3、TLSv1.2 | AUTO | - |
| 对称算法 | AES-256-GCM、SM4 | AUTO | - |
| 非对称算法 | RSA-2048、SM2 | AUTO | - |
| Hash 算法 | SHA-256、SM3、MD5 | INFERRED | MD5 仅用于 etag |
| 伪加密 | 无 | MISSING | 未发现 |
| 随机数 | RAND_bytes、SecureRandom | AUTO | - |
| 默认账号 | 无 | MISSING | 未发现 |
| 监听端口 | 443/TCP、80/TCP | AUTO | - |
| 个人数据 | 邮箱、手机号 | AUTO | 邮箱加密存储，手机号明文 ⚠ |
| root 启动 | 否 | AUTO | - |

### 子报告索引

- [密码学详细 finding](./report-密码学-{name}-{date}.md)
- [网络协议与端口详细 finding](./report-网络-{name}-{date}.md)
- [组件档案详细 finding](./report-组件档案-{name}-{date}.md)

### 声明 vs 实际

| 类别 | 声明 | 实际 | 一致 |
|------|------|------|------|
| 算法 | SM4、SM2、SM3 | AES-256-GCM、SM4、RSA-2048、SM2、SHA-256、SM3、MD5 | ⚠ 声明遗漏 AES/RSA/SHA-256 |
| 协议 | TLSv1.3 | TLSv1.3、TLSv1.2 | ⚠ 实际支持 TLSv1.2 |
```

---

## 5. 调度与失败处理

### 5.1 Phase 1 派发

两批并行：

- **批 A**：6 老 scanner + 3 新 scanner = 9 个 subagent 并行
- **批 B**：不需要

### 5.2 失败阈值（按比例调整）

| 失败数 | 行为 |
|--------|------|
| 1 个 | 重试 2 次（退避 0s/5s/15s） |
| 2 个 | 重试 + 标记维度 FAILED 但不影响主流程 |
| 3-4 个 | 部分降级，继续其他维度 |
| ≥ 5 个 | Phase 级降级，收集已完成结果 |

### 5.3 Verdict 阶段去重

`crypto-scanner` 与 `secret-scanner` 都会在源码中检测同一类模式（如 `MD5` 调用、`AES` 调用、加密库导入），因此在 verdict 阶段按以下规则去重：

- 同一 `file + line + check_item`（如 `foo.c:42:insecure_hash`）出现在两个 scanner 的 findings 中时，保留 severity 更高的一条；若 severity 相同，保留 `confidence` 更高的一条；若都相同则保留 crypto-scanner 的 finding（crypto-scanner 是该检查项的归属维度）。
- 同一 `file + line` 范围内（±5 行）出现多个相关 finding（如一个 `MD5()` 调用既被 secret-scanner 识别为弱哈希又被 crypto-scanner 识别为不安全算法），合并为一条 finding，evidence 拼接两者的证据。

---

## 6. 共享 patterns 与知识库

### 6.1 新增 reference 文件

| 文件 | 用途 | 引用方 |
|------|------|--------|
| `references/patterns-crypto.md` | 算法/伪加密/随机数 patterns | crypto-scanner + secret-scanner |
| `references/patterns-network.md` | 协议/端口 patterns | network-scanner |
| `references/library-vuln-caps.md` | 库版本→不安全能力表 | crypto + network + component-info |
| `references/red-line-rules.md` | 全量红线规则（10 类别） | 所有 scanner |
| `references/personal-data-patterns.md` | 个人数据字段名正则 | component-info-scanner |

### 6.2 库版本知识库策略（多机制联动）

1. 优先读 `*-lock.*` / `*.lock` / `*-sum.*` 文件（lock 优先）
2. 退到主声明文件（`package.json`、`go.mod`、`requirements.txt`、`pom.xml`、`Cargo.toml`、`vcpkg.json`、`conanfile.txt`）
3. 读不到任何依赖文件 → 产出 `MISSING_LOCK_FILE` WARN finding

启动时尝试拉 NVD/OSV 离线快照（24h 内缓存），失败回落内置知识库。`dependency-check.md` 加网络可达性预检。

### 6.3 外部工具

沿用现有 6 维度的工具集（grep/find/file/stat/checksec/readelf/objdump/xxd/python3）。新增：

- `jq`（解析 JSON 依赖文件）
- `xmllint`（解析 XML 依赖文件）

缺失时降级策略与现有工具一致：在 `dependency-check.md` 中标注 `required` / `degradable`，并通过 `question` 工具询问用户。

### 6.4 跨语言 pattern 覆盖（梯级）

| Tier | 语言 | pattern 质量 |
|------|------|-------------|
| Tier-1 | C/C++、Go、Python、Java | 高质量 |
| Tier-2 | JavaScript、TypeScript、Rust、C#、PHP、Ruby | 基础 |
| 其他 | 其他 | 无 pattern，标记 INFO |

---

## 7. 测试策略

### 7.1 Fixture

| 路径 | 用途 |
|------|------|
| `tests/fixtures/crypto-test/` | MD5 密码用途、DES、RC4、伪加密、Math.random、SecureRandom、SM4、SM2、SM3 |
| `tests/fixtures/network-test/` | SSL3.0、Telnet、TLSv1.2、TLSv1.3、bind/listen 端口、配置端口 |
| `tests/fixtures/component-info-test/` | Django B/S、Qt C/S、admin/123456 默认账号、phone 字段、setuid 二进制、docker privileged |
| `tests/fixtures/full-test-component-info/` | 端到端 fixture：1 个完整组件，3 个 scanner 联合产生 component-info 档案 |
| `tests/fixtures/expected/crypto-expected.json` | crypto 测试预期 baseline |
| `tests/fixtures/expected/network-expected.json` | network 测试预期 baseline |
| `tests/fixtures/expected/component-info-expected.json` | component-info 测试预期 baseline |
| `tests/fixtures/expected/component-info-summary-expected.json` | summary JSON 预期 baseline |

### 7.2 验证脚本

```bash
python3 -m json.tool tests/fixtures/expected/crypto-expected.json >/dev/null
python3 -m json.tool tests/fixtures/expected/network-expected.json >/dev/null
python3 -m json.tool tests/fixtures/expected/component-info-expected.json >/dev/null
python3 -m json.tool tests/fixtures/expected/component-info-summary-expected.json >/dev/null
```

---

## 8. security-scanner 自身建档

仓库根提交 `component-info.md`，按 9 字段填表。预期大部分字段是 `MISSING` 或 `无`（scanner 本身不监听端口、不采个人数据、不用 root），但能起到模板示例作用。

| 字段 | 预期值 |
|------|--------|
| 架构类型 | 不涉及（scanner 是 SKILL 指令包，不是可执行服务） |
| 通信协议 | 不涉及 |
| 算法 | 不涉及（scanner 不实现密码学） |
| 伪加密 | 不涉及 |
| 随机数 | 不涉及 |
| 默认账号 | 无 |
| 端口 | 无 |
| 个人数据 | 无（scanner 不采集任何用户数据） |
| root 启动 | 否（普通用户权限即可运行） |

---

## 9. 文件变更清单

### 9.1 新增文件

```
security-scanner/
├── scanners/
│   ├── crypto-scanner.md           # 新增
│   ├── network-scanner.md          # 新增
│   └── component-info-scanner.md   # 新增
├── references/
│   ├── patterns-crypto.md          # 新增
│   ├── patterns-network.md         # 新增
│   ├── library-vuln-caps.md        # 新增
│   ├── red-line-rules.md           # 新增
│   └── personal-data-patterns.md   # 新增
├── templates/
│   ├── report-密码学.md            # 新增
│   ├── report-网络.md              # 新增
│   └── report-组件档案.md          # 新增
├── tests/
│   └── fixtures/
│       ├── crypto-test/            # 新增
│       ├── network-test/           # 新增
│       ├── component-info-test/    # 新增
│       ├── full-test-component-info/  # 新增
│       └── expected/
│           ├── crypto-expected.json
│           ├── network-expected.json
│           ├── component-info-expected.json
│           └── component-info-summary-expected.json
├── docs/
│   └── superpowers/
│       └── specs/
│           └── 2026-06-29-component-info-archive-design.md   # 本文档
└── component-info.md               # self-disclosure 示范
```

### 9.2 修改文件

| 文件 | 变更 |
|------|------|
| `SKILL.md` | 加入 3 个新维度的触发条件、加载路径、finding schema 扩展（library/version 在 evidence） |
| `orchestration/orchestrator.md` | 加入 3 个新维度的派发逻辑、阈值调整、verdict 去重规则 |
| `orchestration/reporter.md` | 加入双产出逻辑、3 个新专项报告生成、Overview 章节生成 |
| `orchestration/reconnaissance.md` | 扩展 Scan Plan schema：增加 crypto/network/component_info 三个 segment |
| `references/dependency-check.md` | 加入 jq/xmllint 检测、NVD/OSV 网络可达性检测 |
| `README.md` | 扫描维度表加入 3 个新维度；项目结构图加入新文件；输出格式表加入 3 个新报告；常见问题增加 component-info 说明 |

---

## 10. 风险与回退

### 10.1 风险

| 风险 | 缓解 |
|------|------|
| 报告爆炸（200+ finding） | Overview/Index 模式：综合报告只给类目级总览，详细 finding 全部进子报告 |
| 误报率高（第三方库默认能力） | 启发式规则带 `false_positive_pattern` 过滤；verdict 阶段复核 |
| 库版本知识库过期 | 启动时尝试拉 NVD/OSV 离线快照；标注知识库最后更新时间 |
| 9 字段推断错误 | 多源交集 → AUTO；单源 → INFERRED；无源 → MISSING + 提示人工补全 |
| 现有 6 维度不受影响 | library/version 信息塞进 evidence 字符串，不改主 schema |

### 10.2 回退

3 个新 scanner 全部失败时，Phase 1 走原有 6 维度 + 综合报告不出现 component-info 概览章节。主 finding JSON 仍可被现有 6 维度消费。

---

## 11. 验收标准

- [ ] crypto-scanner 能识别至少 5 个常见算法（MD5、DES、3DES、RC4、SHA-256）+ 2 个伪加密 pattern + 2 个随机数 API
- [ ] network-scanner 能识别至少 4 个协议（SSL3.0、TLS1.0、TLS1.2、TLS1.3）+ 端口
- [ ] component-info-scanner 能推断 B/S / C/S / 不涉及 / MISSING 四种架构结论
- [ ] 9 字段全部能产出 `value` + `confidence` + `label` + `inference_note` + `reverse_evidence`
- [ ] 综合报告顶部"组件档案概览"章节生成
- [ ] 3 个子报告生成
- [ ] component-info-summary-{name}-{date}.json 生成
- [ ] security-scanner 自身的 component-info.md 生成
- [ ] 所有 fixture 通过 `python3 -m json.tool` 校验
- [ ] 现有 6 维度不受影响（`security-scan-report-*.json` 仍可被消费）
- [ ] 审计点 A0-A3 全部通过

---

## 12. 开放问题

无。grill-me 与 brainstorming 阶段已经收敛所有争议点。
