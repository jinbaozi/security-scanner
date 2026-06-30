# redline 条款切片：dependency

> 本文件由 `scripts/slice_redline_clauses.py` 从 `references/redline-mapping.md` 生成。
> 仅包含 `automation` 为 `full` 或 `partial` 且映射到当前维度的条款；manual 条款不注入 scanner。

```yaml
redline_clauses:
  - clause_id: 2.1.1
    rl_ids: ["RL-200"]
    automation: partial
    profile_min: kylin-redline-p0
    summary: >-
      系统须经漏洞扫描工具扫描，高风险级别的漏洞必须得到解决或有效规避。
    manual_note: >-
      可自动识别 CVSS >= 7 的公开漏洞；漏洞扫描工具版本、插件配置和规避有效性需人工或外部工具确认。
  - clause_id: 2.1.2
    rl_ids: ["RL-201"]
    automation: partial
    profile_min: kylin-redline-p0
    summary: >-
      产品使用的开源或三方件等存在外部公开漏洞，已有官方修复方案的，产品无论是否调用都必须按照官方认可的方案修复；产品梳理所使用到的开源及第三方软件，并输出开源及第三方软件清单
    manual_note: >-
      可自动生成 SBOM 并关联公开漏洞；官方修复方案适用性和未调用组件是否仍需修复需人工确认。
  - clause_id: 12.1.1
    rl_ids: ["RL-202"]
    automation: partial
    profile_min: kylin-redline-p0
    summary: >-
      产品所使用的下属所有平台版本组件、开源和三方件组件要求使用最新版本，禁止使用EOM后的平台组件或老旧的三方组件。
    manual_note: >-
      可基于 manifest/SBOM 识别 EOM/EOL 和老旧组件；平台组件生命周期资料和最新版本策略需人工确认。
```
