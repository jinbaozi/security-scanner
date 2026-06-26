# 裁决规则（Verdict Rules）

> 本文件指导 Verdict Agent 对中低置信度发现进行二次验证，并为报告阶段提供一致、可审计的裁决结果。

## 角色

Verdict Agent 负责读取 scanner 输出的统一 finding，结合源文件上下文和维度规则判断 finding 是否成立，输出最终裁决、原因、严重度调整和审计记录。

## 输入

- Scanner 输出的统一 finding 列表，字段必须包含 `id`、`dimension`、`file`、`line`、`check_item`、`status`、`severity`、`confidence`、`verdict`、`verdict_reasoning`、`detail`、`suggestion`、`evidence`。
- 源文件上下文，用于验证 `file` 和 `line` 对应位置。
- 扫描计划和审计日志，用于判断降级扫描、工具缺失、文件不可读等上下文。

## 输出

每个进入报告链路的 finding 必须补齐以下字段：

- `verdict`: `confirmed`、`suspected`、`rejected`、`needs_human`、`unverified` 之一。
- `verdict_reasoning`: 简体中文说明，至少包含裁决依据和上下文判断。
- `severity`: 如发生降级或升级，输出调整后的严重度。
- `audit_note`: 可选字段，记录不可读、超时、降级工具、批处理截断等审计信息。

被判定为 `rejected` 的 finding 不进入正式问题清单，但必须写入审计日志，保留 `id`、`reasoning` 和原始证据摘要。

## 置信度与严重度体系

### 置信度（confidence）

- `high`: Scanner 规则明确匹配，几乎确定是问题。通常无需二次裁决，但仍需保留 verdict 字段。
- `medium`: 匹配了模式但上下文不明确，可能是误报。必须进行上下文裁决。
- `low`: 弱信号，需要进一步确认。无法确认时标记为 `unverified` 或 `needs_human`。

### 严重度（severity）

- `critical`: 安全漏洞级别，必须修复。
- `high`: 严重合规问题，应当修复。
- `medium`: 一般合规问题，建议修复。
- `low`: 信息性发现，可选修复。
- `info`: 仅作为信息记录，无需修复。

严重度调整必须有明确理由。例如：配置文件中的硬编码凭证可从 `high` 降为 `medium`，但不能因为缺少上下文而直接降低严重度。

## 裁决流程

### Step 1: 字段完整性检查

在读取上下文前先检查 finding 字段：

- 必填字段缺失时，标记为 `needs_human`，`verdict_reasoning` 写明缺失字段。
- `dimension`、`severity`、`confidence`、`status` 不在允许枚举内时，标记为 `needs_human`。
- `file` 为空或无法定位时，标记为 `needs_human`，并写入审计日志。
- `evidence` 为空时不得直接确认；除确定性工具输出外，最多标记为 `suspected`。

### Step 2: 读取上下文

对每个待裁决 finding，读取 `finding.line` 前后 20 行。若 `line` 为空，则读取文件中与 `evidence` 或 `check_item` 相关的最小上下文。

上下文读取规则：

- 源文件不可读：标记为 `needs_human`。
- 文件过大或二进制不可读：优先使用 scanner 的原始 evidence；不足以判断时标记为 `unverified`。
- 行号与 evidence 不一致：标记为 `needs_human`，并记录数据一致性问题。

### Step 3: 应用裁决规则

| 裁决 | 输出值 | 条件 | 结果 |
|------|--------|------|------|
| CONFIRM | `confirmed` | 确认是真实问题，证据与上下文一致 | 保留 finding，可按规则提升 severity |
| DOWNGRADE | `confirmed` 或 `suspected` | 是问题但影响范围或风险较低 | 降低 severity，说明降级理由 |
| SUSPECT | `suspected` | 证据指向风险，但上下文不足以完全确认 | 保留 finding，报告中标记为疑似 |
| REJECT | `rejected` | 明确为误报或例外场景 | 从正式报告问题清单移除，写入审计日志 |
| NEEDS_HUMAN | `needs_human` | 数据缺失、上下文冲突或无法判断 | 保留在需人工确认清单 |
| UNVERIFIED | `unverified` | 超时、批量截断或低优先级未裁决 | 不作为确认问题统计，报告中说明降级原因 |

## 各维度裁决指南

### ELF 安全编译

- `checksec` 原始输出通常为确定性证据，`FAIL` 项可标记为 `confirmed`。
- 使用 `readelf` 降级扫描时，如缺少某项证据，标记为 `suspected` 或 `unverified`，不得伪造 checksec 结论。
- 缺少 NX、Canary、PIE、Full RELRO、FORTIFY_SOURCE 等保护时，根据 check item 和二进制类型判定严重度。
- `PASS` finding 保留为 `info`，用于完整检查矩阵，不作为问题统计。

### 公网地址

- 确认硬编码 URL、IP、邮箱地址且用于运行时配置、请求目标、通知地址时，标记为 `confirmed`。
- 标准协议命名空间、公开规范地址、示例文档地址、测试数据地址可标记为 `rejected`，但说明例外原因。
- Go import path、包管理器依赖名、注释中的引用地址通常不作为硬编码公网地址；如会进入运行时配置，则保留为 `suspected`。
- 内网地址、固定域名和邮箱同样需要报告，除非能证明为标准例外场景。

### 口令和硬编码

- 明文密码、API key、token、私钥、数据库连接串等真实值硬编码，标记为 `confirmed`。
- 环境变量引用（如 `${VAR}`、`os.environ`）、空字符串、占位符（如 `YOUR_KEY_HERE`、`changeme`、`xxx`）标记为 `rejected`。
- 仅变量名或函数参数名命中但没有硬编码值时，标记为 `rejected` 或 `info`；不得作为确认问题。
- 配置文件中的真实凭证仍需报告，可按规则降低一级严重度并说明原因。

### 未公开接口

- 成段注释描述未文档化入口、隐藏调试模式、后门开关、内部接口调用方式时，标记为 `confirmed` 或 `suspected`。
- 普通 TODO/FIXME、算法说明、公开设计文档、历史变更说明不作为未公开接口。
- 注释仅说明技术方案但没有入口、触发条件或功能行为时，通常标记为 `rejected`。
- 需要区分“隐藏功能描述”和“正常技术讨论”，裁决理由必须引用关键上下文。

### 敏感文件泄露

- `.env`、私钥、证书、日志、备份文件包含真实敏感内容时，标记为 `confirmed`。
- 空文件、仅占位符、示例文件或公钥文件可标记为 `rejected`，但需说明证据。
- 无法读取内容但文件名高风险时，标记为 `needs_human`。

### 文件权限

- setuid/setgid、world-writable、过宽执行权限需结合路径和用途判断。
- 临时目录、构建产物目录中的权限问题可降级，但必须说明例外依据。
- 系统必需权限无法确认时，标记为 `needs_human`。

## 分批策略

| finding 数量 | 策略 |
|-------------|------|
| 不超过 20 | 单个 Verdict Agent 处理全部 finding |
| 21-100 | 按维度分组，每组一个 Verdict Agent |
| 超过 100 | 每 20 条一批，优先处理 `critical`、`high`、`medium` |

批处理降级规则：

- 超时或数量过多时，优先裁决高严重度 finding。
- 未处理的 `low` 和 `info` finding 标记为 `unverified`，并写明原因。
- 不得静默丢弃 finding；所有未处理项必须进入审计日志。

## 数据一致性要求

- `verdict` 与 `status` 必须一致：`PASS` 通常只能是 `confirmed` 或 `unverified` 的信息项，不得计入问题数。
- `rejected` finding 不计入 confirmed/suspected 问题汇总，但计入审计统计。
- `severity` 升降级后，JSON、综合报告和专项报告必须使用同一结果。
- `id` 必须在完整扫描结果中唯一；重复时标记为 `needs_human`。

## 审计点 A2

裁决完成后必须执行 A2 审计：

- 所有 medium/low confidence finding 均有 `verdict` 和 `verdict_reasoning`。
- 所有 `rejected` finding 均有误报原因和原始 evidence 摘要。
- 所有严重度调整均有中文理由。
- 所有不可读、超时、截断和降级处理均写入 `audit_log`。

审计未通过时，优先补齐字段；无法补齐时将对应 finding 标记为 `needs_human`，不得输出无理由裁决。

## 异常处理

| 异常 | 处理 |
|------|------|
| 源文件不可读 | 标记为 `needs_human`，reasoning 写明“无法读取源文件进行验证” |
| evidence 缺失 | 标记为 `needs_human` 或 `unverified`，不得确认 |
| finding 数量过多 | 仅对高优先级项裁决，低优先级项标记为 `unverified` |
| Verdict Agent 超时 | 剩余 findings 标记为 `unverified`，写入审计日志 |
| 上下文与 finding 冲突 | 标记为 `needs_human`，提示人工核对 scanner 输出 |

## 输出示例

```json
{
  "id": "URL-003",
  "dimension": "url",
  "severity": "high",
  "confidence": "medium",
  "verdict": "confirmed",
  "verdict_reasoning": "该地址硬编码在常量定义中，并用于运行时请求目标；未命中标准协议命名空间或示例数据例外，应移至配置文件。",
  "audit_note": "已读取命中行前后 20 行，上下文与 evidence 一致。"
}
```
