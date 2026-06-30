# redline 条款切片：integrity

> 本文件由 `scripts/slice_redline_clauses.py` 从 `references/redline-mapping.md` 生成。
> 仅包含 `automation` 为 `full` 或 `partial` 且映射到当前维度的条款；manual 条款不注入 scanner。

```yaml
redline_clauses:
  - clause_id: 10.1.1
    rl_ids: ["RL-220"]
    automation: partial
    profile_min: redline-full
    summary: >-
      产品对外发布的软件（包含软件包/补丁包）必须提供完整性校验机制，在安装、升级过程中对软件进行完整性验证
    manual_note: >-
      可检测 RPM/DEB 签名元数据和构建/安装脚本校验步骤；安装升级过程是否实际验证需人工或动态验证。
```
