# redline 条款切片：fileleak

> 本文件由 `scripts/slice_redline_clauses.py` 从 `references/redline-mapping.md` 生成。
> 仅包含 `automation` 为 `full` 或 `partial` 且映射到当前维度的条款；manual 条款不注入 scanner。

```yaml
redline_clauses:
  - clause_id: 4.1.1
    rl_ids: ["RL-160", "RL-161", "RL-162", "RL-180", "RL-181", "RL-182", "RL-217", "RL-218", "RL-219"]
    automation: partial
    profile_min: kylin-redline-p0
    summary: >-
      禁止存在可绕过系统安全机制（认证、权限控制、日志记录）对系统或数据进行访问的功能。 • 禁止隐秘访问方式：包括隐藏账号、隐藏口令、无鉴权的隐藏模式命令/参数、隐藏组合键访问方式；隐藏的协议/端口/服务；隐藏的生产命令/端口、调测命令/端口 • 禁止不可管理的认证/访问方式：包括用户不可管理的账号，人机接口以及可远程访问的机机接口的硬编码口令。
    manual_note: >-
      可检测硬编码凭据、调试密钥、隐藏后门关键词和默认账号信号；是否构成绕过安全机制需人工裁决。
    terminology_pending: true
  - clause_id: 4.3.1
    rl_ids: ["RL-246"]
    automation: partial
    profile_min: kylin-redline-full
    summary: >-
      禁止在产品软件中存留可能被质疑的组件，包括第三方的网络嗅探、调试工具、开发/编译工具、仅在调测阶段使用的认证密钥、自研调试工具/脚本。
    manual_note: >-
      可检测 tcpdump、gdb、strace、nmap、gcc、JDK、调试脚本等交付包残留；组件用途和例外需人工确认。
```
