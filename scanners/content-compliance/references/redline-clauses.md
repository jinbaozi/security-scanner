# redline 条款切片：content-compliance

> 本文件由 `scripts/slice_redline_clauses.py` 从 `references/redline-mapping.md` 生成。
> 仅包含 `automation` 为 `full` 或 `partial` 且映射到当前维度的条款；manual 条款不注入 scanner。

```yaml
redline_clauses:
  - clause_id: 13.1.1
    rl_ids: ["RL-230"]
    automation: partial
    profile_min: kylin-redline-full
    summary: >-
      产品系统中的任何文字、地图、图表的描述中，关于国家、地区、领土、民族、语言等政治敏感信息的描述要符合国家政治要求，不得违反国家正式的政治表述和立场。
    manual_note: >-
      可检测明确禁词和错称；地图、图表、政治表述语境需人工审查，默认 WARN + needs_human。
```
