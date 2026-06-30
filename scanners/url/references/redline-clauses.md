# redline 条款切片：url

> 本文件由 `scripts/slice_redline_clauses.py` 从 `references/redline-mapping.md` 生成。
> 仅包含 `automation` 为 `full` 或 `partial` 且映射到当前维度的条款；manual 条款不注入 scanner。

```yaml
redline_clauses:
  - clause_id: 4.3.2
    rl_ids: ["RL-143"]
    automation: partial
    profile_min: redline-p0
    summary: >-
      禁止在产品软件中包含用户界面不可见或产品资料未描述的未公开的公网地址（包括公网IP地址、公网URL地址/域名、邮箱地址）。
    manual_note: >-
      可检测公网 IP、URL、域名和邮箱；是否已在界面或产品资料公开需人工对照资料。
  - clause_id: 6.1.2
    rl_ids: ["RL-105", "RL-143"]
    automation: partial
    profile_min: redline-p0
    summary: >-
      在非信任网络之间进行敏感数据的传输须采用安全传输通道或者加密后传输，有标准协议规定除外。
    manual_note: >-
      可检测敏感字段经 HTTP 或不安全协议传输；敏感数据范围、非信任网络边界和标准协议例外需人工确认。
    terminology_pending: true
  - clause_id: 9.1.1
    rl_ids: ["RL-140", "RL-141", "RL-142", "RL-143", "RL-144"]
    automation: partial
    profile_min: redline-full
    summary: >-
      涉及个人数据的采集/处理的功能须提供安全保护机制（如认证、权限控制、日志记录等），并通过产品资料向客户公开。
    manual_note: >-
      可检测个人数据字段、明文存储/传输和日志信号；资料公开声明和保护机制完整性需人工确认。
```
