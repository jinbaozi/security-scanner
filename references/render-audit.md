# 渲染审计（A4 Audit Checkpoint）

> 在 Phase 3 报告生成之后、视为最终输出之前执行。本文件定义 A4 审计点、必填/可选占位符契约以及降级路径。

## 角色

A4 审计由 Orchestrator 调用 `scripts/audit_render.py` 自动执行，目的是捕获渲染阶段残留的占位符（最常见的原因是模板变量与渲染器之间的命名不一致，例如 `{}` 与 f-string 冲突）。该审计点是 **A3 内容审计的姊妹检查**，专注于"渲染是否完整"，不重复评判 finding 内容本身。

## 模板契约

每个 `templates/*.md` 必须在文件首部声明 YAML frontmatter 形式的 contract：

```markdown
---
required:
  - COMPONENT_NAME
  - SCAN_DATE
  - TOTAL_FILES
optional:
  - DURATION_SECONDS
  - AUDIT_NOTES
---

# Report for [[COMPONENT_NAME]]
Date: [[SCAN_DATE]]
Total: [[TOTAL_FILES]]
Duration: [[DURATION_SECONDS]] sec
Notes: [[AUDIT_NOTES]]
```

占位符语法为 `[[UPPER_SNAKE_CASE]]`，**禁止使用**：

- `{name}` —— 与 f-string 冲突，f-string 会主动求值，未定义变量触发 `NameError`。
- `${name}` —— `string.Template` 默认语法，可能与文档中的 `$PATH` 等环境变量示例混淆。
- `<NAME>` —— 与 HTML/XML 标签冲突。

## 审计流程

### Step 1: 调用 `scripts/render_template.py`

Phase 3 报告生成阶段必须调用：

```bash
python3 scripts/render_template.py \
    --template templates/report-comprehensive.md \
    --values security-reports/values-comprehensive.yaml \
    --output security-reports/security-scan-report-${COMP}-${DATE}.md
```

返回值与 `strict` 模式：

| 模式 | 行为 |
|------|------|
| 默认（safe） | 缺占位符保留为 `[[NAME]]`，渲染继续，缺失列表写入 `*.missing.json` sidecar |
| `--strict` | 必填占位符缺失时退出码 4，渲染拒绝；可选缺失仍保留字面量 |

### Step 2: 调用 `scripts/audit_render.py`

```bash
python3 scripts/audit_render.py \
    --rendered security-reports/security-scan-report-${COMP}-${DATE}.md \
    --template templates/report-comprehensive.md \
    --output security-reports/security-scan-report-${COMP}-${DATE}.audit.json
```

返回 JSON 中 `status` 字段：

| Status | 触发条件 | 退出码 | 后续处理 |
|--------|----------|--------|----------|
| `pass` | 无任何残留占位符 | 0 | 报告作为最终输出 |
| `warn` | 仅 optional 或 unknown 残留 | 3 | 报告输出，附录添加"[渲染备注] N 个占位符未替换" |
| `fail` | 任意 required 残留 | 4 | 重新渲染，最多 2 次；仍失败标 degraded |

### Step 3: 综合判定

A4 与 A3 审计结果合并形成最终报告状态：

| A3 | A4 | 最终状态 |
|----|----|----------|
| PASS | pass | `PASS` |
| PASS | warn | `PASS + 渲染备注` |
| PASS | fail | `WARN + 重新渲染` |
| WARN | pass / warn | `WARN` |
| WARN | fail | `FAIL` |
| FAIL | * | `FAIL` |

## 异常处理

| 异常 | 处理 |
|------|------|
| 模板无 frontmatter contract | 视为"无必填约束"；所有残留 placeholder 触发 warn |
| `render_template.py` 自身报错（语法错误、模板不存在） | 退出码非 0，报告生成中断，进入降级路径 |
| 必填占位符连续 2 次渲染仍失败 | 标记 `degraded`，写入 `audit_log`，输出报告标"渲染未完成" |
| Sidecar `.missing.json` 文件保留 | 作为审计追溯依据，30 天后可清理 |

## 与 f-string 的兼容性边界

`scripts/render_template.py` 必须保持 f-string 安全：

- 不允许在 `render_template.py` 内部用 f-string 渲染用户模板——会重新引入同一问题。
- 不允许把 `values` 字典通过 `format(**values)` 传给模板——`{` 在模板里仍是有效字符。
- 唯一允许的渲染机制：`string.Template.safe_substitute`（默认）或 `string.Template.substitute`（strict）。

## 占位符命名规范

| 前缀 | 用途 | 示例 |
|------|------|------|
| `META_*` | 元数据 | `META_COMPONENT`, `META_DATE` |
| `STAT_*` | 统计计数 | `STAT_TOTAL_FILES`, `STAT_CRITICAL_COUNT` |
| `SECTION_*` | 维度章节正文 | `SECTION_ELF_FINDINGS`, `SECTION_URL_FINDINGS` |
| `TABLE_*` | 表格内容 | `TABLE_REDLINE_COVERAGE` |
| `AUX_*` | 辅助段落 | `AUX_AUDIT_NOTES`, `AUX_DEGRADATION_NOTE` |

任何不在白名单的占位符仍可被解析，但审计脚本会标记为 `unknown_unfilled` 供人工复核。

## 参考示例

### 模板迁移（从 `{var}` 到 `[[VAR]]`）

提供 `scripts/migrate_placeholders.py`（可选辅助脚本）：

```python
# 将 templates/*.md 中的 {var} 占位符批量转换为 [[VAR]]
# 仅转换与 Python f-string 兼容的 identifier 命名；保留合法代码片段。
```

迁移规则：

1. 必须是 `[a-z_][a-z0-9_]*` 命名（与小写一致）。
2. 不在 `{ }` 内嵌套其他 `{` 或 `}`。
3. 不在代码块（``` ```）或行内代码（`` ` ``）内。
4. 转大写：`{elf_findings}` → `[[ELF_FINDINGS]]`。

人工 review 迁移后的模板，确认无遗漏或误转。