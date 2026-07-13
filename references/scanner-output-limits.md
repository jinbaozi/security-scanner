# Scanner Finding 输出上限

> 本规则限制注入模型和 scanner session 返回的 finding 数量，不允许静默丢失原始证据。

## 默认门禁

- 单个维度单次输出的 finding 上限 200。
- 原始命中、工具输出和完整路径写入 `security-reports/evidence/<dimension>/`，不得直接回显。
- 超过 200 时先按 `file + check_item + verdict + redline_clause` 聚合重复项，再按 `critical > high > medium > low > info` 保留代表性 finding。
- critical/high 不得因低严重度大量命中而被截断。
- 聚合 finding 必须给出命中总数、代表样本和原始证据引用。

## 审计字段

发生聚合或截断时，维度 audit log 至少包含：

```json
{
  "original_count": 1200,
  "emitted_count": 200,
  "truncated_count": 1000,
  "strategy": "severity_then_file_check_item_aggregation",
  "evidence_ref": "security-reports/evidence/secret/raw-matches.jsonl"
}
```

`truncated_count` 表示未作为独立 finding 注入模型的数量，不代表证据被删除。Phase 2/3 可按 `evidence_ref` 定点复核，但不得读取整份原始证据到 Pi 上下文。
