# 依赖与漏洞 Patterns 库

> 本文件集中维护 Dependency Scanner 使用的 manifest、lock、SBOM 和库版本识别规则。

## Manifest 与 Lock 文件

| 生态 | Manifest | Lock / SBOM |
|------|----------|-------------|
| Node.js | `package.json` | `package-lock.json`, `pnpm-lock.yaml`, `yarn.lock` |
| Python | `requirements.txt`, `pyproject.toml`, `Pipfile` | `poetry.lock`, `Pipfile.lock` |
| Java | `pom.xml`, `build.gradle`, `build.gradle.kts` | `gradle.lockfile`, Maven dependency tree |
| Go | `go.mod` | `go.sum` |
| Rust | `Cargo.toml` | `Cargo.lock` |
| PHP | `composer.json` | `composer.lock` |
| Ruby | `Gemfile` | `Gemfile.lock` |
| SBOM | `*.cdx.json`, `bom.json` | CycloneDX |
| SBOM | `*.spdx.json`, `*.spdx` | SPDX |

## 缺失 Lock 判定

| Manifest | 期望 Lock | 缺失 finding |
|----------|-----------|--------------|
| `package.json` | `package-lock.json` / `pnpm-lock.yaml` / `yarn.lock` | `MISSING_LOCK_FILE` |
| `pyproject.toml` | `poetry.lock` | `MISSING_LOCK_FILE` |
| `Pipfile` | `Pipfile.lock` | `MISSING_LOCK_FILE` |
| `go.mod` | `go.sum` | `MISSING_LOCK_FILE` |
| `Cargo.toml` | `Cargo.lock` | `MISSING_LOCK_FILE` |
| `composer.json` | `composer.lock` | `MISSING_LOCK_FILE` |
| `Gemfile` | `Gemfile.lock` | `MISSING_LOCK_FILE` |

## 版本提取 Pattern

| 生态 | Pattern |
|------|---------|
| npm | `"(?P<name>[^"]+)"\s*:\s*"(?P<version>[\^~]?[0-9][^"]*)"` |
| Python requirements | `^(?P<name>[A-Za-z0-9_.-]+)==(?P<version>[0-9][^\s;]+)` |
| Maven | `<groupId>(?P<group>[^<]+)</groupId>[\s\S]{0,200}<artifactId>(?P<name>[^<]+)</artifactId>[\s\S]{0,200}<version>(?P<version>[^<]+)</version>` |
| Go | `(?P<name>[a-zA-Z0-9_./-]+)\s+v(?P<version>[0-9][^\s]+)` |
| Cargo | `name\s*=\s*"(?P<name>[^"]+)"[\s\S]{0,120}version\s*=\s*"(?P<version>[^"]+)"` |
| Vendored | `(?P<name>openssl|zlib|sqlite|curl|busybox)[-/ ](?P<version>[0-9]+\.[0-9][A-Za-z0-9._-]*)` |

## 漏洞与评分

| 信号 | 判定 |
|------|------|
| `cvss >= 9.0` | `critical` / `FAIL` |
| `cvss >= 7.0` | `high` / `FAIL` |
| `4.0 <= cvss < 7.0` | `medium` / `WARN` |
| 无 CVSS 但有 CVE | `medium` / `needs_human` |

## SBOM 输出字段

每个依赖项至少包含：`name`、`version`、`ecosystem`、`source`、`confidence`。
