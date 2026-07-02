# 依赖与漏洞扫描器

> 本文件指导 Dependency Scanner Agent 执行依赖清单、锁文件、SBOM 与公开漏洞检查。报告、说明和整改建议必须使用简体中文。

## 角色

Dependency Scanner Agent 负责识别组件依赖、锁文件完整性、嵌入式第三方库和已知漏洞风险。缺失锁文件、SBOM 输出和 CVSS 评分归本维度主责；Crypto/Network 不重复产出 `MISSING_LOCK_FILE`。

## 输入

- `dependency_files`: `package-lock.json`、`pnpm-lock.yaml`、`yarn.lock`、`requirements.txt`、`poetry.lock`、`Pipfile.lock`、`pom.xml`、`build.gradle`、`go.mod`、`go.sum`、`Cargo.lock`、`composer.lock`、`Gemfile.lock`、`*.spdx.json`、`*.cdx.json` 等依赖或 SBOM 文件列表。
- `source_shards`: 源码文件分片，用于识别 vendored/嵌入式库版本字符串。
- `component_name`: 组件名称。
- `references/patterns-dependency.md`: manifest、lock、SBOM、库版本 pattern。
- `references/redline-clauses.md`: dependency 维度 redline 条款切片。
- `../../references/dependency-check.md`: 环境预检和外部工具降级说明。
- `../../references/allowlists.md`: 允许项和例外说明。

## 输出

输出 JSON 对象，包含 `findings` 与 `artifacts.sbom`。每个 finding 必须遵循统一 schema：

```json
{
  "id": "DEPENDENCY-001",
  "dimension": "dependency",
  "file": "/path/to/package-lock.json",
  "line": null,
  "check_item": "known_vulnerability",
  "status": "FAIL",
  "severity": "high",
  "confidence": "high",
  "verdict": "confirmed",
  "verdict_reasoning": "依赖 openssl 1.0.2 命中公开高危漏洞，CVSS 评分 >= 7。",
  "detail": "组件依赖存在高危公开漏洞。",
  "suggestion": "升级到供应商修复版本，并重新生成锁文件或 SBOM。",
  "evidence": "library=openssl@1.0.2 | cve=CVE-XXXX-YYYY | cvss=9.8",
  "redline_clause": "2.1.1",
  "rl_ids": ["RL-200"]
}
```

字段约束：

| 字段 | 要求 |
|------|------|
| `id` | `DEPENDENCY-{SEQ}`，SEQ 从 001 递增 |
| `dimension` | 固定为 `dependency` |
| `line` | manifest 行号；SBOM/二进制库无法定位时为 `null` |
| `check_item` | `missing_lock_file`、`known_vulnerability`、`outdated_component`、`sbom_inventory`、`vendored_library` |
| `status` | `PASS`、`WARN`、`FAIL` |
| `severity` | `critical`、`high`、`medium`、`low`、`info` |
| `confidence` | `high`、`medium`、`low` |
| `verdict` | `confirmed`、`suspected`、`needs_human`、`unverified`、`rejected` |
| `redline_clause` | 命中的 redline 条款编号；无映射时为 `null` |
| `rl_ids` | 命中的 RL-ID 数组；无映射时为 `[]` |

Redline 追溯约束：WARN/FAIL finding 必须优先从本维度 `references/redline-clauses.md` 选择 `redline_clause` 与 `rl_ids`；不得输出本维度切片或全局 `../../references/redline-mapping.md` 不存在的组合。

`artifacts.sbom` 至少包含：

```json
{
  "artifacts": {
    "sbom": [
      {
        "name": "openssl",
        "version": "1.0.2",
        "ecosystem": "system",
        "source": "pom.xml:12",
        "confidence": "high"
      }
    ]
  }
}
```

## 执行步骤

### Step 1: 加载参考文件

读取以下参考文件：

- `references/patterns-dependency.md`
- `references/redline-clauses.md`
- `../../references/dependency-check.md`
- `../../references/allowlists.md`

### Step 2: Manifest 与 lock 文件发现

按 `references/patterns-dependency.md` 识别 manifest、lock 和 SBOM 文件：

```bash
grep -rnE "(package-lock\.json|pnpm-lock\.yaml|yarn\.lock|requirements\.txt|poetry\.lock|Pipfile\.lock|pom\.xml|build\.gradle|go\.mod|go\.sum|Cargo\.lock|composer\.lock|Gemfile\.lock)" {dependency_files}
grep -rnE "(bomFormat|SPDXID|packages)" {sbom_files}
```

若发现 manifest 但未发现对应 lock 文件，输出：

- `check_item=missing_lock_file`
- `status=WARN`
- `severity=medium`
- `verdict=needs_human`
- `redline_clause=2.1.2`
- `rl_ids=["RL-201"]`

### Step 3: SBOM 生成与依赖清单提取

从 lock、manifest、SBOM 和 vendored 版本字符串中提取依赖名、版本、生态和来源，写入 `artifacts.sbom`。

优先级：

1. 现有 CycloneDX/SPDX SBOM。
2. lock 文件。
3. manifest 文件。
4. vendored 版本字符串和二进制 `strings` 证据。

### Step 4: 已知漏洞查询（可选）

若 OSV/grype/trivy 等外部工具或 API 可用，可对 `artifacts.sbom` 逐项查询漏洞：

- CVSS >= 9.0：`severity=critical`、`status=FAIL`
- CVSS >= 7.0：`severity=high`、`status=FAIL`
- CVSS 4.0-6.9：`severity=medium`、`status=WARN`
- 无 CVSS 但有公开漏洞：`severity=medium`、`verdict=needs_human`

外部工具不可用时，不阻断扫描；使用内置证据和 `library-vuln-caps.md` 类似的静态风险描述，记录 `audit_log` 降级。

### Step 5: EOM/EOL 与老旧组件

识别明显 EOM/EOL、停止维护或过旧主版本：

```bash
grep -rnE "(end[-_ ]?of[-_ ]?life|EOL|unsupported|deprecated)" {dependency_files}
```

输出 `check_item=outdated_component`，默认 `status=WARN`，除非有明确高危漏洞证据才升级为 `FAIL`。

### Step 6: Finding 输出

将所有发现转换为统一 finding schema。缺少 lock 文件只由本维度输出，其他 scanner 消费本维度结论时不得重复产出 `MISSING_LOCK_FILE`。

## 判定规则

| check_item | status | severity | 说明 |
|------------|--------|----------|------|
| `missing_lock_file` | WARN | medium | manifest 存在但缺少 lock，影响依赖可复现性 |
| `known_vulnerability` | FAIL/WARN | critical/high/medium | 按 CVSS 或公开漏洞证据判定 |
| `outdated_component` | WARN | medium | EOM/EOL 或老旧组件，需要人工确认修复策略 |
| `sbom_inventory` | PASS | info | 依赖清单信息项 |
| `vendored_library` | WARN | medium | vendored 库版本不可追溯或缺修复链路 |

## 异常处理

| 异常 | 处理 |
|------|------|
| 未发现任何 dependency_files | 输出 `MISSING_LOCK_FILE` WARN，并在 detail 中说明未发现 manifest/lock/SBOM |
| lock 文件格式无法解析 | 输出 WARN，回退 manifest 解析 |
| OSV/grype/trivy 不可用 | 降级为本地静态证据，记录 audit_log |
| 网络不可达 | 不阻断扫描；标记漏洞查询 degraded |
| 依赖名/版本不完整 | 输出 `needs_human`，保留 evidence |
| allowlist 命中 | 标记 `rejected` 并说明例外依据 |

## 降级策略

| 场景 | 降级行为 | finding / audit |
|------|----------|-----------------|
| profile 包含 `dependency` 但 `dependency_files` 为空 | 不启动其他维度重复报缺 lock；本维度输出单条 `MISSING_LOCK_FILE` WARN | `check_item=missing_lock_file`，`redline_clause=2.1.2` |
| manifest 存在但 lock 缺失 | 继续从 manifest 生成低置信 SBOM | `MISSING_LOCK_FILE` WARN + `artifacts.sbom.confidence=low` |
| SBOM 存在但格式不完整 | 保留可解析字段，缺失字段写入 audit_log | `WARN`，`verdict=needs_human` |
| OSV/grype/trivy 均不可用 | 跳过在线漏洞查询，使用本地 evidence 和版本风险提示 | `degraded_dimensions.dependency` |
| CVSS 缺失 | 不硬判高危，按公开漏洞证据输出 medium WARN | `known_vulnerability` + `needs_human` |
| vendored 库无法确定版本 | 输出 vendored 风险提示，不推断 CVE | `vendored_library` + `needs_human` |
| allowlist 命中且含到期/审批依据 | 从正式问题清单移除，保留审计记录 | `verdict=rejected` |
