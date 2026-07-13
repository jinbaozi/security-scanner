# 口令和硬编码扫描器

> 本文件指导 Secret Scanner Agent 执行口令、密钥、Token、私钥等硬编码凭证扫描。报告、说明和整改建议必须使用简体中文。不得向用户回显已读 reference 全文或完整文件清单。

## 有界工具输出（强制）

模式搜索必须使用本维 `references/credential-candidates.regex`，该资源由 `meta.yaml` 以 `scope=tool` 登记，只允许交给 `$SKILL_ROOT/scripts/safe_grep.py` 本地加载。文件清单必须先由 `resolve_artifact.py` 从规范化 Scan Plan 解析；禁止猜测文件名、创建 `/tmp` 规则、使用进程替换或执行裸 `grep/find`。默认最多保留 200 条样本、32 KiB JSON，完整计数保留在文件中且终端只输出一行。单维 finding 上限 200；超限按严重度和 file/check_item 聚合，audit_log 必须记录 `truncated_count`，原始命中写 evidence 文件且不得回显。

## 角色

Secret Scanner Agent 仅负责检测源码和配置文件中的硬编码凭证，不负责 URL、注释、ELF 或权限问题。

## 输入

- `source_shards`: 源码文件分片列表
- `config_files`: 配置文件列表
- `component_name`: 源码组件名称
- `references/credential-candidates.regex`: 版本化凭证候选规则，仅由本地工具加载
- `references/redline-clauses.md`: secret 维度 redline 条款切片。

## 输出

输出 JSON 对象，`findings` 中每个元素必须符合统一 finding schema（Orchestrator 注入 finding-schema；字段定义见该文件）。最小示例如下：

```json
{
  "id": "SECRET-001",
  "dimension": "secret",
  "file": "/path/to/config.yaml",
  "line": 4,
  "check_item": "hardcoded_password",
  "status": "FAIL",
  "severity": "high",
  "confidence": "high",
  "verdict": "confirmed",
  "verdict_reasoning": "该字段在配置文件中以明文具体值赋值，非环境变量引用、占位符或空值。",
  "detail": "配置文件中发现疑似真实数据库密码，属于硬编码凭证",
  "suggestion": "使用环境变量、密钥管理服务或加密配置文件，不要在交付包中明文保存密码",
  "evidence": "password: \"real_database_password_123\"",
  "redline_clause": "4.1.1",
  "rl_ids": ["RL-217"]
}
```

字段约束：

| 字段 | 要求 |
|------|------|
| `id` | `SECRET-{SEQ}`，SEQ 从 001 递增 |
| `dimension` | 固定为 `secret` |
| `line` | 匹配所在行；无法定位时为 `null` |
| `check_item` | `hardcoded_password`、`hardcoded_api_key`、`hardcoded_token`、`private_key`、`encoded_secret`、`credential_keyword`、`auth_key`、`encryption_key`、`logged_credential` |
| `status` | 最终输出仅使用 `PASS`、`WARN`、`FAIL`；跳过或未知情况统一输出为 `WARN` 并在 detail 中说明 |
| `severity` | `critical`、`high`、`medium`、`low`、`info` |
| `confidence` | `high`、`medium`、`low` |
| `verdict` | 高置信真实凭证为 `confirmed`，不确定项为 `needs_human` 或 `unverified`，误报为 `rejected` |
| `verdict_reasoning` | 简体中文裁决依据，说明凭证类型、赋值上下文、过滤规则和是否疑似真实凭证 |
| `redline_clause` | 命中的 redline 条款编号；无映射时为 `null` |
| `rl_ids` | 命中的 RL-ID 数组；无映射时为 `[]` |

Redline 追溯约束：WARN/FAIL finding 必须优先从本维度 `references/redline-clauses.md` 选择 `redline_clause` 与 `rl_ids`；不得输出本维度 `references/redline-clauses.md` 未定义的条款组合。

## 执行步骤

### Step 1: Layer 1 - 确定性候选提取

Orchestrator 先调用 `resolve_artifact.py`，从 `scan-plan.normalized.json` 分别解析 source/config 清单；读取其紧凑 JSON 中的 `list_path` 作为 `$FILES_LIST`，不得自行生成清单。每个已解析清单执行：

```bash
python3 "$SKILL_ROOT/scripts/safe_grep.py" \
  --pattern-file "$SKILL_ROOT/scanners/secret/references/credential-candidates.regex" \
  --files-file "$FILES_LIST" \
  --base-root "$MATERIALIZED_ROOT" \
  --max-count 200 --max-bytes 32768 \
  --output "$REPORT_ROOT/evidence/secret-candidates.json"
```

### Step 2: Layer 1.5 - 强格式候选

私钥头、云访问键、Token 前缀、赋值上下文和日志凭据规则均已固化在版本化规则文件中。命中仅为 candidate，必须执行后续过滤、脱敏和上下文复核。

### Step 3: Layer 2 - 模式过滤

排除以下明显非敏感匹配：

1. 函数声明或参数定义：如 `def authenticate(username, password)`。
2. 文档注释：仅说明“密码”“加密”等概念，无实际值。
3. import/include 语句：如 `from crypto import encrypt`。
4. 类型声明无赋值：如 `var password string`。
5. 环境变量引用：如 `os.environ.get("PASSWORD")`、`${DB_PASSWORD}`、`process.env.API_KEY`。
6. 占位符：`YOUR_API_KEY_HERE`、`changeme`、`example`、`xxx`、`<password>`。
7. 空值或 null：`password: ""`、`secret: null`。
8. 测试断言中明确的假数据可降级为 `severity=low`，但不要直接丢弃。

### Step 4: Layer 3 - 上下文判断

对 Layer 2 过滤后剩余的每个匹配，阅读前后 15 行，判断：

1. 是否为真实凭证：具体字符串、长度大于 8、包含混合字符、非变量引用、非占位符。
2. 凭证类型：明文密码、API 密钥、加解密密钥、访问 Token、SSH/PEM 私钥、编码凭证。
3. 存储位置：源码硬编码、配置文件硬编码、测试文件、文档样例、日志输出路径。
4. 是否可公开：任何真实凭证或私钥均不应进入交付包。

## 判定规则

### confidence

- `high`: 明确硬编码的实际凭证值，或匹配私钥/AWS Key 等强格式。
- `medium`: 可疑赋值但可能是测试数据、示例值或动态生成值。
- `low`: 仅变量名或参数名匹配，无实际赋值。

### severity

- `critical`: 私钥、生产 Token、云访问密钥、可直接登录的真实凭证。
- `high`: 源码中的明文密码、API Key、访问 Token。
- `high`: 认证密钥、签名密钥、加密工作密钥、日志中输出的凭据字段。
- `medium`: 配置文件中的硬编码凭证，或疑似编码凭证。
- `low`: 测试数据、示例配置中的疑似凭证。
- `info`: 仅关键字命中但无实际值，一般不进入最终问题列表。

AWS Access Key ID 的特殊判定：

- `AKIA...` 单独出现时通常为 `severity=medium`，因为 Access Key ID 本身不是完整 secret。
- 同时发现 AWS Secret Access Key（40 位 Base64 风格字符串）时升为 `severity=critical`。
- 在配置文件、生产常量或部署脚本的赋值上下文中出现时，至少为 `severity=high`。

### 配置文件专项检查

对 `.conf`、`.yaml`、`.yml`、`.ini`、`.properties`、`.env` 等配置清单复用同一版本化规则和 `safe_grep.py`，不得另行执行裸 grep。配置文件中的硬编码凭证通常 severity 降低一级，但真实生产凭证、私钥和云密钥不得降级。

## 异常处理

| 异常 | 处理 |
|------|------|
| 关键字匹配超过 500 条 | 提高 Layer 2 过滤阈值，仅保留有赋值、私钥头或强格式的匹配 |
| 大型二进制文件误匹配 | 通过 `file` 命令排除非文本文件 |
| UTF-16 等编码文件 | 尝试 `iconv` 转换；失败则跳过并记录 |
| evidence 含真实密钥 | evidence 只保留前后少量字符并做脱敏，例如 `sk-prod-xy...abc` |
| 凭据路径同时命中 fileleak | 保留源码硬编码 finding；若是密钥文件路径泄露，Verdict 阶段由 fileleak/permission 路径证据优先 |
