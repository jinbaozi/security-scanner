# Finding Schema

> Scanner、Verdict、Reporter 共用。仅在 Phase 1.5 / Phase 2 / Phase 3 需要时加载；勿在 SKILL 激活时预读。

## 统一格式

```json
{
  "id": "{DIMENSION}-{SEQ}",
  "dimension": "comment|url|secret|fileleak|permission|elf|network|crypto|component-info|dependency|secure-coding|integrity|content-compliance",
  "file": "文件绝对路径",
  "line": "integer | string | null",
  "check_item": "检查项名称",
  "status": "PASS|WARN|FAIL",
  "severity": "critical|high|medium|low|info",
  "confidence": "high|medium|low",
  "verdict": "confirmed|suspected|rejected|needs_human|unverified",
  "verdict_reasoning": "裁决理由（简体中文）",
  "detail": "问题描述（简体中文）",
  "suggestion": "修复建议（简体中文）",
  "evidence": "证据（代码片段或命令输出）",
  "redline_clause": "条款编号或 null",
  "rl_ids": ["RL-XXX"]
}
```

## `line` 按维度解释

| 维度 | line 类型 | 示例 |
|------|-----------|------|
| `comment` | `string` | `"36-50"` |
| `url` / `secret` | `integer` | `45` |
| `fileleak` / `permission` / `elf` | `null` 或 `integer` | `null` |
| `network` / `crypto` / `component-info` / `dependency` | `integer` 或 `null` | `9` |
| `secure-coding` | `integer` 或 `string` | `"18-24"` |
| `integrity` | `null` 或 `integer` | `null` |
| `content-compliance` | `integer`、`string` 或 `null` | `"LICENSE:12"` |

## evidence 扩展

`crypto` / `network` / `component-info` / `dependency` / `secure-coding` / `integrity` / `content-compliance` 的 `evidence` 可含：

`library=NAME@VERSION | library_version=VERSION | trigger=REASON | cve=CVE-XXXX-XXXXX`

老 6 维（comment/url/secret/fileleak/permission/elf）不解析此格式。

## Redline 绑定

WARN/FAIL 必须优先从本维 `references/redline-clauses.md` 选择 `redline_clause` 与 `rl_ids`；不得绑定切片未定义的组合。无映射时 `redline_clause=null` 且 `rl_ids=[]`。
