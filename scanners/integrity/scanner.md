# 完整性校验扫描器

> 本文件指导 Integrity Scanner Agent 执行交付物完整性检查，包括 RPM/DEB 签名元数据、构建/安装脚本中的 gpg/cosign/sha256sum 校验以及来源可信证据。报告、说明和整改建议必须使用简体中文。

## 角色

Integrity Scanner Agent 负责判断交付包是否具备可验证的完整性保护信号。不负责漏洞版本扫描、密码学算法强度或内容合规文本审查。

## 输入

- `package_files`: RPM、DEB、tarball、镜像清单等交付物文件列表。
- `config_files` / `build_files`: 构建脚本、安装脚本、CI 配置、release 脚本。
- `dependency_findings`（可选）：Dependency Scanner 的 SBOM，用于定位交付物和第三方组件。
- `component_name`: 组件名称。
- `references/redline-clauses.md`: integrity 维度 redline 条款切片。
- `../../references/allowlists.md`: 白名单和例外规则。

## 输出

```json
{
  "id": "INTEGRITY-001",
  "dimension": "integrity",
  "file": "/path/to/package.rpm",
  "line": null,
  "check_item": "package_signature",
  "status": "WARN",
  "severity": "medium",
  "confidence": "medium",
  "verdict": "needs_human",
  "verdict_reasoning": "发现 RPM 包但未能验证签名元数据，需要人工或 rpm 工具确认。",
  "detail": "交付物签名状态未验证。",
  "suggestion": "使用 rpm --checksig 或供应链签名系统验证，并保留校验记录。",
  "evidence": "package=example.rpm | signature=unverified",
  "redline_clause": "10.1.1",
  "rl_ids": ["RL-220"]
}
```

字段约束：

| 字段 | 要求 |
|------|------|
| `id` | `INTEGRITY-{SEQ}`，SEQ 从 001 递增 |
| `dimension` | 固定为 `integrity` |
| `line` | 脚本行号；包元数据无法定位时为 `null` |
| `check_item` | `package_signature`、`checksum_verification`、`provenance_signature`、`integrity_missing` |
| `status` | `PASS`、`WARN`、`FAIL` |
| `severity` | `critical`、`high`、`medium`、`low`、`info` |
| `confidence` | `high`、`medium`、`low` |
| `verdict` | `confirmed`、`suspected`、`needs_human`、`unverified`、`rejected` |
| `redline_clause` | 命中的 redline 条款编号；无映射时为 `null` |
| `rl_ids` | 命中的 RL-ID 数组；无映射时为 `[]` |

Redline 追溯约束：WARN/FAIL finding 必须优先从本维度 `references/redline-clauses.md` 选择 `redline_clause` 与 `rl_ids`；不得输出本维度切片或全局 `../../references/redline-mapping.md` 不存在的组合。

## 执行步骤

### Step 1: RPM/DEB 签名元数据检测

```bash
rpm --checksig {rpm_files}
dpkg-sig --verify {deb_files}
debsigs --verify {deb_files}
```

判定：

- 签名存在且验证通过：`check_item=package_signature`、`status=PASS`、`severity=info`。
- 包存在但工具缺失或无法验证：`status=WARN`、`verdict=needs_human`。
- 明确签名缺失：`status=WARN`、`severity=medium`；若发布要求强制签名且无例外，Verdict 可升为 `FAIL`。

### Step 2: 构建/安装脚本校验 pattern

```bash
grep -rnE "\b(gpg|gpgv)\s+--verify\b|cosign\s+verify|sha256sum\s+-c|shasum\s+-a\s+256\s+-c|openssl\s+dgst\s+-sha256" {build_and_install_files}
grep -rnE "curl\s+[^|>]+(http|https).*(sh|bash)|wget\s+[^|>]+(http|https)" {build_and_install_files}
```

判定：

- 下载/安装远端包且存在签名或 checksum 校验：`PASS/info`。
- 下载远端包但未发现校验：`WARN/medium`，`check_item=checksum_verification`。
- 使用 gpg/cosign 但忽略失败退出码：`WARN/medium`。

### Step 3: 来源可信/供应链签名

识别 `cosign sign`、`cosign attest`、SLSA provenance、GitHub attestation 等信号。仅发现签名流程时输出 `PASS/info`；签名声明和实际交付物无法对应时输出 `needs_human`。

### Step 4: Finding 输出

将包元数据和脚本证据转换为统一 finding schema。无法验证时不得伪造 PASS，必须使用 `WARN` / `unverified`。

## 判定规则

| check_item | 默认 status | severity | 说明 |
|------------|-------------|----------|------|
| `package_signature` | PASS/WARN | info/medium | RPM/DEB 签名元数据 |
| `checksum_verification` | PASS/WARN | info/medium | sha256sum/gpg/cosign 校验脚本 |
| `provenance_signature` | PASS/WARN | info/medium | provenance/attestation 信号 |
| `integrity_missing` | WARN | medium | 有交付物但未发现任何完整性校验证据 |

## 异常处理

| 异常 | 处理 |
|------|------|
| 非 RPM/DEB 包 | 检查 tarball/镜像/安装脚本校验信号；无法确认时 `needs_human` |
| rpm/dpkg-sig/debsigs 缺失 | 不阻断；记录 degraded，并输出 `unverified` |
| 包文件过大或不可读 | 输出 WARN，保留路径和文件类型 evidence |
| 脚本下载命令复杂 | 输出 `needs_human`，列出下载与校验片段 |
| 签名工具输出解析失败 | 保留原始输出摘要，标记 `unverified` |
| allowlist 命中 | 标记 `rejected` 并说明例外依据 |

## 降级策略

| 场景 | 降级行为 | 最终状态 |
|------|----------|----------|
| 无包文件且无构建/安装脚本 | 条件 skip，报告标注“无适用输入” | skip |
| rpm/debsigs/cosign 缺失 | 仅检查脚本文本信号 | degraded |
| 只有 checksum 无签名 | 输出 WARN，建议补充签名或可信发布链 | `needs_human` |
| 只有签名声明无可验证文件 | 输出 WARN，要求人工提供发布证据 | `unverified` |
