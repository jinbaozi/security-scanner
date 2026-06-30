# redline 条款切片：elf

> 本文件由 `scripts/slice_redline_clauses.py` 从 `references/redline-mapping.md` 生成。
> 仅包含 `automation` 为 `full` 或 `partial` 且映射到当前维度的条款；manual 条款不注入 scanner。

```yaml
redline_clauses:
  - clause_id: 11.2.1
    rl_ids: ["RL-260"]
    automation: partial
    profile_min: kylin-redline-p0
    summary: >-
      产品必须按规范开启安全编译选项。
    manual_note: >-
      ELF 侧可检测栈保护、NX、RELRO、PIE、BIND_NOW、RPATH 等；内核 ASLR=2 属运行时配置人工项。
```
