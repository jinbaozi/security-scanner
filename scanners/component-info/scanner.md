# 组件信息扫描器

> 本文件指导 Component-Info Scanner Agent 执行组件级元数据检测，包括架构类型推断、默认账号识别、个人数据字段违规处理（明文存储 / HTTP 传输 / 日志明文）、以及是否需要 root 权限运行（SUID / privileged / capabilities 多源交集）。报告、说明和整改建议必须使用简体中文。

## 角色

Component-Info Scanner Agent 仅负责检测源码模型字段、配置文件、容器清单（Dockerfile / docker-compose.yml / Kubernetes manifest）中的组件元信息，不负责密码学算法、网络协议、ELF 安全编译、注释或权限（chmod/SUID 本身）问题。

## 输入

- `source_shards`: 源码文件分片列表
- `config_files`: 配置文件列表
- `component_name`: 源码组件名称
- `references/personal-data-patterns.md`: 个人数据字段名与违规处理 pattern 库
- `../../references/red-line-rules.md`: 红线规则库（RL-140 ~ RL-159 个人数据、RL-160 ~ RL-179 默认账号）
- `../../references/allowlists.md`: 白名单与例外规则
- `references/architecture-signals.md`: 架构类型推断信号库（Django/Flask/Spring/Express/Gin/Telnet/socket 等）

## 输出

输出 JSON 对象，`findings` 中每个元素必须遵循统一 finding schema：

```json
{
  "id": "INFO-001",
  "dimension": "component_info",
  "file": "/path/to/app.py",
  "line": 5,
  "check_item": "personal_data",
  "status": "FAIL",
  "severity": "critical",
  "confidence": "high",
  "verdict": "confirmed",
  "verdict_reasoning": "id_card 字段明文存储，命中红线 RL-140",
  "detail": "身份证号字段以明文 CharField 存储",
  "suggestion": "改用加密存储 + 脱敏显示",
  "evidence": "id_card = models.CharField(max_length=18)"
}
```

字段约束：

| 字段 | 要求 |
|------|------|
| `id` | `INFO-{SEQ}`，SEQ 从 001 递增 |
| `dimension` | 固定为 `component_info` |
| `line` | 匹配所在行；无法定位时为 `null` |
| `check_item` | `architecture`、`default_account`、`personal_data`、`requires_root` |
| `status` | 最终输出仅使用 `PASS`、`WARN`、`FAIL`；跳过或未知情况统一输出为 `WARN` 并在 detail 中说明 |
| `severity` | `critical`、`high`、`medium`、`low`、`info` |
| `confidence` | `high`、`medium`、`low` |
| `verdict` | 高置信真实问题为 `confirmed`，不确定项为 `needs_human` 或 `unverified`，误报为 `rejected` |
| `verdict_reasoning` | 简体中文裁决依据，说明架构信号、字段名、上下文用途、白名单命中情况和是否命中红线 |

## 执行步骤

### Step 1: 加载参考文件

读取以下参考文件以加载检测规则：

- `references/personal-data-patterns.md`：个人数据字段名 pattern 库（姓名、手机号、身份证、邮箱、位置、设备标识、银行卡、出生日期、头像、IP 地址），覆盖 snake_case / camelCase / PascalCase 三种命名约定；违规处理 pattern（明文存储 RL-140/RL-141/RL-142、HTTP 明文传输 RL-143、邮箱明文日志 RL-144）
- `../../references/red-line-rules.md`：红线规则库（RL-140 ~ RL-159 个人数据违规处理、RL-160 ~ RL-179 默认账号未披露）
- `../../references/allowlists.md`：白名单与例外规则
- `references/architecture-signals.md`：架构类型推断信号库（B/S 框架、DNS 服务、嵌入式 socket 等）

### Step 2: Layer 1 - 架构类型推断

按语言/配置执行架构信号扫描（`references/architecture-signals.md` 第 1 节）：

```bash
# B/S 架构（Web 框架）
grep -rnE "django\.(db|http)|flask\.Flask|fastapi\.FastAPI|springframework|SpringApplication|express\(\)|gin\.Default|laravel|rails" {all_files}

# C/S 架构（桌面 GUI）
grep -rnE "import\s+(tkinter|wx|swing|javafx)|using\s+System\.Windows\.Forms|QMainWindow|gtk" {all_files}

# 嵌入式/单机服务（裸 socket / daemon）
grep -rnE "socket\.socket|telnetlib\.|net\.Listen|ServerSocket|TcpListener" {all_files}
```

命中框架后输出 `check_item=architecture` 的 finding：

- B/S 框架（Django/Flask/Spring/Express/Gin/Laravel/Rails）→ `verdict=B/S 架构（Web 应用）`、`severity=info`、`status=PASS`
- C/S GUI（tkinter/wx/swing/javafx/Qt/GTK）→ `verdict=C/S 架构（桌面应用）`、`severity=info`、`status=PASS`
- 嵌入式 socket/telnetlib → `verdict=嵌入式或单机服务`、`severity=info`、`status=PASS`
- 无明确信号 → `verdict=unknown`、`severity=info`、`status=WARN`

### Step 3: Layer 2 - 默认账号识别

执行默认账号 pattern 匹配（`../../references/red-line-rules.md` RL-160 ~ RL-162）：

```bash
# RL-160: admin/admin123/password
grep -rnE "['\"]admin['\"]\s*[,;:=]\s*['\"](?:admin|123456|password|admin123|Admin@123)['\"]" {all_files}

# RL-161: root/root/toor
grep -rnE "['\"]root['\"]\s*[,;:=]\s*['\"](?:root|toor|123456|password)['\"]" {all_files}

# RL-162: 数据库 init 脚本默认账号
grep -rnE "INSERT\s+INTO\s+\w+\s+VALUES\s*\([^)]*['\"](?:admin|root)['\"]" {sql_files}

# 常量定义形式（Python/Go/Java）
grep -rnE "(?:ADMIN_USER|ADMIN_PASS|DEFAULT_USER|DEFAULT_PASSWORD|USER_DEFAULT|PASS_DEFAULT)\s*=\s*['\"][^'\"]+['\"]" {all_files}
```

命中后输出 `check_item=default_account`、`severity=high`、`status=FAIL` 的 finding，并关联 RL-160 / RL-161 / RL-162。

### Step 4: Layer 3 - 个人数据字段违规处理

按 `references/personal-data-patterns.md` 第 1 节字段名 pattern 匹配，第 2 节违规处理 pattern 输出 finding：

```bash
# 字段名识别（snake_case / camelCase / PascalCase 三种命名约定）
grep -rnE "\b(?:name|username|real_name|full_name|user_name)\b\s*[:=]" {all_files}
grep -rnE "\b(?:phone|mobile|tel|cellphone|phone_number|mobile_number)\b\s*[:=]" {all_files}
grep -rnE "\b(?:id_card|idcard|identity|id_number|identity_card|citizen_id)\b\s*[:=]" {all_files}
grep -rnE "\b(?:email|mail|e_mail|email_address)\b\s*[:=]" {all_files}
grep -rnE "\b(?:bank_card|card_number|credit_card|cc_number)\b\s*[:=]" {all_files}

# 违规处理检测
# RL-140/RL-141/RL-142: 明文存储
grep -rnE "(?:id_card|idcard|phone|mobile|email|bank_card|identity).{0,80}(?:=|:)\s*[\"'][^\"']{4,}[\"']" {all_files}

# RL-143: HTTP 明文传输
grep -rnE "http://[^\"'\s]*(?:id_card|phone|idcard|mobile|email|bank_card|identity_card)" {all_files}

# RL-144: 邮箱明文日志
grep -rnE "logger\.(?:info|debug|error|warn|fatal)\s*\([^)]*(?:email|mail|phone|mobile|id_card|idcard)\b" {all_files}
```

排除规则（命中下列关键字之一时不告警）：
- 上下文 80 字符内出现 `encrypt|hash|mask|hmac|bcrypt|cipher|secrets\.|SystemRandom`
- 日志上下文出现 `mask|redact|truncate|hash|md5|sha`

命中后输出 `check_item=personal_data` 的 finding，severity 默认为：
- `id_card` / `bank_card` → `critical`（RL-140 / RL-142）
- `phone` / `mobile` → `high`（RL-141）
- HTTP 明文传输个人数据 → `high`（RL-143）
- 邮箱明文日志 → `medium`（RL-144）

### Step 5: Layer 4 - 是否需要 root（多源交集）

按多源信号交叉验证 root 需求，单一弱信号输出 `WARN`，多源交集输出 `FAIL`：

```bash
# 弱信号 1：SUID 位（Dockerfile / install 脚本）
grep -rnE "chmod\s+(?:[0-7]*[u]?s|[0-7]{3,4})" {dockerfile_files} {install_files} {shell_scripts}

# 弱信号 2：容器 privileged 模式
grep -rnE "^\s*privileged\s*:\s*true" {compose_files} {k8s_files}

# 弱信号 3：Linux capabilities（高危集）
grep -rnE "^\s*cap_add\s*:" {compose_files}
grep -rnE "^\s*-\s*(?:SYS_ADMIN|SYS_PTRACE|SYS_RAWIO|NET_ADMIN|NET_RAW|SYS_MODULE)\b" {compose_files} {k8s_files}

# 弱信号 4：监听特权端口（< 1024）且无 user 切换
grep -rnE "^\s*(?:port|listen|Listen|EXPOSE)\s*[:=]?\s*[0-9]{1,3}\b" {all_files}

# 弱信号 5：使用 0-1023 端口且无 setcap / getcap
grep -rnE "\b(?:bind|listen)\s*\([^)]*(?:['\"]?:[1-9][0-9]{0,2}|[0-9]{1,3})\)" {all_files}
```

判定逻辑：

- **FAIL**（高置信 root 需求）：同时满足 ≥ 2 个弱信号（如 `privileged: true` + `cap_add: SYS_ADMIN`；或 SUID + privileged）
- **WARN**（疑似 root 需求）：仅 1 个弱信号（如单独 `privileged: true`，或单独 SUID）
- **PASS**：无任何信号

命中后输出 `check_item=requires_root`、`severity=high`（FAIL）/`medium`（WARN）的 finding。

### Step 6: Finding 输出

将所有 Layer 1-5 命中、且未在白名单中排除的问题，转换为统一 finding schema 输出。

每个 finding 的 id 从 `INFO-001` 开始递增，dimension 固定为 `component_info`。

## 判定规则

### status

- `FAIL`：确认命中红线（RL-140 ~ RL-159 个人数据、RL-160 ~ RL-179 默认账号），或多源信号交集确认为 root 需求。
- `WARN`：可能命中红线但需要人工确认（如单源 root 信号、个人数据明文日志），或字段名命中但上下文不明确。
- `PASS`：仅做信息记录（如 `check_item=architecture` 的纯架构识别，不视为问题）。

### confidence

- `high`：明确命中红线 pattern，且上下文确认为非安全用途。
- `medium`：可疑命中但用途不明（需要人工判断）。
- `low`：仅关键字命中但 pattern 不完整（如裸字符串 "admin" 出现在注释中）。

### severity

| check_item | severity 默认值 | 说明 |
|------------|----------------|------|
| `architecture` | info | 架构类型识别（仅信息记录） |
| `default_account` | high | 硬编码 admin/root 默认账号（RL-160 / RL-161 / RL-162） |
| `personal_data` | critical（id_card / bank_card）/ high（phone / mobile）/ high（HTTP 明文）/ medium（邮箱日志） | 个人数据违规处理（RL-140 ~ RL-144） |
| `requires_root` | high（多源交集）/ medium（单源） | root 需求识别 |

### verdict

- `confirmed`：高置信真实问题，命中红线且上下文确认。
- `suspected`：可能命中红线但需要更多上下文。
- `needs_human`：需要人工审查（如个人数据字段名命中但用途模糊）。
- `rejected`：误报（如测试样例、注释说明、白名单内）。
- `unverified`：无法自动验证。

## 异常处理

| 异常 | 处理 |
|------|------|
| 关键字匹配超过 1000 条 | 提高 Layer 3 字段名过滤阈值，仅保留有明确赋值语句的匹配 |
| 大型二进制文件误匹配 | 通过 `file` 命令排除非文本文件 |
| UTF-16 等编码文件 | 尝试 `iconv` 转换；失败则跳过并记录 |
| 字段名在多种语言中歧义（如 Java `String` 既可存姓名也可存地址） | 输出 `needs_human` 并在 verdict_reasoning 中说明 |
| evidence 含敏感数据 | evidence 保留字段名和上下文，不输出完整身份证号/手机号/银行卡号 |
| 个人数据明文日志上下文模糊 | 输出 `needs_human` 并在 verdict_reasoning 中说明 |
| 容器 manifest 缺少 user 字段但也未明确 privileged | 单源信号输出 `WARN`，提示人工确认 |
| 白名单命中 | 标记 `rejected` 并在 verdict_reasoning 中说明白名单规则 |
