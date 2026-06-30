# redline 条款切片：secure-coding

> 本文件由 `scripts/slice_redline_clauses.py` 从 `references/redline-mapping.md` 生成。
> 仅包含 `automation` 为 `full` 或 `partial` 且映射到当前维度的条款；manual 条款不注入 scanner。

```yaml
redline_clauses:
  - clause_id: 11.1.1
    rl_ids: ["RL-210"]
    automation: partial
    profile_min: redline-full
    summary: >-
      产品代码必须经过静态代码检查工具扫描，并按照工具上相应语言的提示进行清理。
    manual_note: >-
      可摄取或提示 SAST/semgrep/clang-tidy 结果；是否使用指定工具规则集并完成清理需人工确认。
  - clause_id: 11.1.2
    rl_ids: ["RL-211", "RL-212"]
    automation: partial
    profile_min: redline-full
    summary: >-
      产品的代码必须按照相应的编程规范使用安全函数替换不安全函数，禁止不正确的重定义安全函数或不正确的封装安全函数。
    manual_note: >-
      可检测不安全函数、安全函数宏重定义和错误封装 pattern；复杂宏解析歧义需人工裁决。
```
