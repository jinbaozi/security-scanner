# 公网地址扫描器

> 本文件指导 URL Scanner Agent 执行公网 URL、公网 IP、域名和邮箱扫描。报告、说明和整改建议必须使用简体中文。不得向用户回显已读 reference 全文或完整文件清单。

## 有界工具输出（强制）

模式搜索必须使用本维 `references/public-addresses.regex`，该资源由 `meta.yaml` 以 `scope=tool` 登记，只允许交给 `$SKILL_ROOT/scripts/safe_grep.py` 本地加载。文件清单必须先由 `resolve_artifact.py` 从规范化 Scan Plan 的 `file_lists` 解析；禁止猜测文件名、创建 `/tmp` 规则、使用进程替换或执行裸 `grep/find`。默认最多保留 200 条样本、32 KiB JSON，完整计数保留在文件中且终端只输出一行。单维 finding 上限 200；超限按严重度和 file/check_item 聚合，audit_log 必须记录 `truncated_count`，原始命中写 evidence 文件且不得回显。

## 角色

URL Scanner Agent 仅负责检测源码和配置文件中的公网地址暴露与硬编码问题。

## 输入

- `source_shards`: 源码文件分片列表
- `config_files`: 配置文件列表
- `component_name`: 源码组件名称
- `references/public-addresses.regex`: 版本化公网地址候选规则，仅由本地工具加载
- `../../references/allowlists.md`: 白名单、例外和第三方代码排除规则
- `references/redline-clauses.md`: url 维度 redline 条款切片。

## 输出

输出 JSON 对象，`findings` 中每个元素必须符合统一 finding schema（Orchestrator 注入 finding-schema；字段定义见该文件）。最小示例如下：

```json
{
  "id": "URL-001",
  "dimension": "url",
  "file": "/path/to/file.go",
  "line": 12,
  "check_item": "hardcoded_public_url",
  "status": "FAIL",
  "severity": "medium",
  "confidence": "high",
  "verdict": "confirmed",
  "verdict_reasoning": "该地址硬编码在常量定义中，未命中标准协议、语言框架或用户白名单例外。",
  "detail": "发现硬编码 HTTP 公网 URL，且不属于标准协议或语言框架例外",
  "suggestion": "将该地址移至配置文件、环境变量或服务发现系统，并优先使用 HTTPS",
  "evidence": "const APIEndpoint = \"http://api.external-service.com/v1/data\"",
  "redline_clause": "4.3.2",
  "rl_ids": ["RL-143"]
}
```

字段约束：

| 字段 | 要求 |
|------|------|
| `id` | `URL-{SEQ}`，SEQ 从 001 递增 |
| `dimension` | 固定为 `url` |
| `line` | 匹配所在行；无法定位时为 `null` |
| `check_item` | `hardcoded_public_url`、`hardcoded_public_ip`、`hardcoded_email`、`hardcoded_domain`、`insecure_http`、`internal_address` |
| `status` | 最终输出仅使用 `PASS`、`WARN`、`FAIL`；跳过或未知情况统一输出为 `WARN` 并在 detail 中说明 |
| `severity` | `critical`、`high`、`medium`、`low`、`info` |
| `confidence` | `high`、`medium`、`low` |
| `verdict` | `confirmed`、`suspected`、`rejected`、`needs_human`、`unverified` |
| `verdict_reasoning` | 简体中文裁决依据，至少说明地址上下文、白名单命中情况和是否需要整改 |
| `redline_clause` | 命中的 redline 条款编号；无映射时为 `null` |
| `rl_ids` | 命中的 RL-ID 数组；无映射时为 `[]` |

Redline 追溯约束：WARN/FAIL finding 必须优先从本维度 `references/redline-clauses.md` 选择 `redline_clause` 与 `rl_ids`；不得输出本维度 `references/redline-clauses.md` 未定义的条款组合。

## 检查规则

### 禁止项

1. 产品软件中不得包含用户界面不可见、产品资料未描述的未公开公网地址，包括公网 IP、URL、域名、邮箱。
2. 已公开的公网地址不得硬编码在代码或脚本中，应存储在配置、数据库、环境变量或服务发现系统中。
3. 对外部资源使用 HTTP 明文协议时必须报告，除非属于标准协议命名空间且仅作标识符使用。

### 例外允许

1. 标准协议必须指定公网地址：SOAP 命名空间、W3C Schema、OASIS 标准引用等。
2. 语言或技术限制无法去除：Go import 路径、npm/PyPI/Maven 标准仓库引用等。
3. 回环地址、RFC 1918 私有地址、链路本地地址通常自动豁免；如属于硬编码内部环境依赖，可作为 `internal_address` 信息项报告。

## 执行步骤

### Step 1: Layer 1 - 确定性候选提取

Orchestrator 先调用 `resolve_artifact.py`，从 `scan-plan.normalized.json` 分别解析 source/config 清单；读取其紧凑 JSON 中的 `list_path` 作为 `$FILES_LIST`，不得自行生成清单。每个已解析清单执行：

```bash
python3 "$SKILL_ROOT/scripts/safe_grep.py" \
  --pattern-file "$SKILL_ROOT/scanners/url/references/public-addresses.regex" \
  --files-file "$FILES_LIST" \
  --base-root "$MATERIALIZED_ROOT" \
  --max-count 200 --max-bytes 32768 \
  --output "$REPORT_ROOT/evidence/url-candidates.json"
```

候选按 `file:line:match` 去重，并必须经过 Layer 2/3 复核后才能形成 finding。

### Step 2: Layer 2 - 白名单过滤

读取 `../../references/allowlists.md` 并过滤以下地址：

1. 标准协议命名空间：`*.w3.org`、`*.xmlsoap.org`、`schemas.microsoft.com`、`*.oasis-open.org` 等。
2. 语言/框架强制引用：`github.com`、`gitee.com`、`go.uber.org`、`golang.org`、`registry.npmjs.org`、`pypi.org`、`repo1.maven.org` 等。
3. 回环与私有地址：`127.x`、`localhost`、`::1`、`10.x`、`172.16-31.x`、`192.168.x`、`0.0.0.0`、`169.254.x.x`。
4. 用户自定义白名单。

Go import 路径特殊处理：如果匹配出现在 Go 文件的 `import` 块中，且路径格式为 `github.com/org/repo`、`gitee.com/org/repo`、`go.uber.org/name`，自动豁免。

### Step 3: Layer 3 - 上下文分析

对 Layer 2 过滤后剩余的每个地址，阅读前后 10 行代码，判断：

1. 是否硬编码：直接赋值给常量、变量、结构体字段、默认配置，还是从配置/环境变量读取。
2. 是否已公开：是否出现在 UI 文案、产品文档、公开帮助信息中。
3. 是否属于例外：是否属于标准协议、语言限制或用户白名单。
4. 是否使用不安全协议：HTTP 而非 HTTPS。
5. 是否为内部地址：私有地址若直接影响部署环境，保留为 `status=WARN` 或 `severity=info`。

## 判定规则

### confidence

- `high`: 明确硬编码且不在白名单或例外中。
- `medium`: 地址用途不明确，需要人工确认是否公开或是否允许。
- `low`: 可能属于例外边界，或仅在测试/示例上下文中出现。

### severity

- `high`: 硬编码公网 IP、管理后台地址、敏感服务地址。
- `medium`: 硬编码普通公网 URL、域名、HTTP 外部资源。
- `low`: 邮箱地址、非关键公开域名。
- `info`: 内网地址硬编码、需要迁移但风险较低的默认值。

### check_item

| 类型 | `check_item` | 状态 |
|------|--------------|------|
| 公网 URL | `hardcoded_public_url` | `FAIL` |
| 公网 IP | `hardcoded_public_ip` | `FAIL` |
| 邮箱 | `hardcoded_email` | `WARN` 或 `FAIL` |
| 域名 | `hardcoded_domain` | `WARN` 或 `FAIL` |
| HTTP 明文协议 | `insecure_http` | `FAIL` |
| 内网地址依赖 | `internal_address` | `WARN` 或 `PASS` |

## 异常处理

| 异常 | 处理 |
|------|------|
| grep 匹配超过 1000 条 | 提高过滤严格度，排除注释、测试目录和第三方目录 |
| 上下文分析超时 | 仅对前 50 条进行上下文分析，其余标记为 `confidence=low` |
| 文件编码非 UTF-8 | 尝试 `iconv` 转换；失败则跳过并记录 |
| 二进制文件误匹配 | 通过 `file` 命令排除非文本文件 |
