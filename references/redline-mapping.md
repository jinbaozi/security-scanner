# redline 条款映射

> 来源：`references/redline-spec.md`（Sheet1 40 条），并依据 2026-06-30 redline gap design 的 profile、automation 边界整理。
>
> 说明：`RL-001` 至 `RL-199` 优先沿用现有 `references/red-line-rules.md`；`RL-200` 及以后为本轮 redline 扩展计划中的稳定预留 ID，后续任务会补入规则库或 scanner 切片。
>
> Mapping schema：
> - `clause_id`：Sheet1 条款编号，必须覆盖 40 条且唯一。
> - `rl_ids`：关联规则 ID 数组，元素形如 `RL-001`。
> - `scanner_dims`：合法值仅限 `elf`、`url`、`secret`、`comment`、`fileleak`、`permission`、`network`、`crypto`、`component-info`、`dependency`、`secure-coding`、`integrity`、`content-compliance`。
> - `automation`：合法值仅限 `full`、`partial`、`manual`。
> - `profile_min`：合法值仅限 `kylin-redline-p0`、`kylin-redline-full`、`kylin-redline-binary`。
> - `terminology_pending`：可选；Sheet2/Sheet3 术语定义缺失影响判定时为 `true`。
> - `manual_note`：可选；说明人工确认边界或 partial 项的人工裁决点。
>
> Task 1b 切片规则：仅将 `automation` 为 `full` 或 `partial` 且 `scanner_dims` 非空的条款切入各维度 `redline-clauses.md`；`automation: manual` 必须保持 `scanner_dims: []`，只供综合报告人工清单和 A3b 覆盖矩阵使用，不注入 scanner，也不由自动 scanner 直接硬判 `FAIL`。

```yaml
redline_mapping:
  - clause_id: "1.1.1"
    rl_ids: ["RL-240"]
    scanner_dims: ["network"]
    automation: partial
    profile_min: "kylin-redline-p0"
    terminology_pending: true
    manual_note: "可自动提取监听端口和端口清单；端口必要性、通信矩阵完整性及动态端口合理范围需人工结合资料确认。"

  - clause_id: "1.1.2"
    rl_ids: ["RL-241"]
    scanner_dims: []
    automation: manual
    profile_min: "kylin-redline-full"
    manual_note: "管理接口认证机制及缺省启用状态属于设计/运行时验证项；scanner 仅可对 Telnet/FTP 等明显无安全通道配置输出 WARN。"

  - clause_id: "2.1.1"
    rl_ids: ["RL-200"]
    scanner_dims: ["dependency"]
    automation: partial
    profile_min: "kylin-redline-p0"
    manual_note: "可自动识别 CVSS >= 7 的公开漏洞；漏洞扫描工具版本、插件配置和规避有效性需人工或外部工具确认。"

  - clause_id: "2.1.2"
    rl_ids: ["RL-201"]
    scanner_dims: ["dependency"]
    automation: partial
    profile_min: "kylin-redline-p0"
    manual_note: "可自动生成 SBOM 并关联公开漏洞；官方修复方案适用性和未调用组件是否仍需修复需人工确认。"

  - clause_id: "3.1.1"
    rl_ids: ["RL-242"]
    scanner_dims: []
    automation: manual
    profile_min: "kylin-redline-full"
    manual_note: "每个授权请求是否校验用户权限属于业务逻辑和运行时访问控制审查，自动 scanner 不硬判 FAIL。"

  - clause_id: "3.1.2"
    rl_ids: ["RL-243"]
    scanner_dims: []
    automation: manual
    profile_min: "kylin-redline-full"
    manual_note: "最终认证是否在服务端完成需要结合架构与运行时链路审查，自动 scanner 不硬判 FAIL。"

  - clause_id: "3.1.3"
    rl_ids: ["RL-080", "RL-081", "RL-082", "RL-083", "RL-084", "RL-244"]
    scanner_dims: ["crypto"]
    automation: partial
    profile_min: "kylin-redline-p0"
    manual_note: "可检测弱随机数生成 session 标识和部分未 regenerate 信号；认证成功后是否必然换发会话标识需人工或动态测试确认。"

  - clause_id: "4.1.1"
    rl_ids: ["RL-160", "RL-161", "RL-162", "RL-180", "RL-181", "RL-182", "RL-217", "RL-218", "RL-219"]
    scanner_dims: ["secret", "comment", "fileleak", "component-info"]
    automation: partial
    profile_min: "kylin-redline-p0"
    terminology_pending: true
    manual_note: "可检测硬编码凭据、调试密钥、隐藏后门关键词和默认账号信号；是否构成绕过安全机制需人工裁决。"

  - clause_id: "4.1.2"
    rl_ids: ["RL-181", "RL-182", "RL-219"]
    scanner_dims: ["comment"]
    automation: partial
    profile_min: "kylin-redline-p0"
    terminology_pending: true
    manual_note: "可检测注释中的隐藏命令、参数、端口和调测入口；公开或受限公开状态需人工对照产品资料。"

  - clause_id: "4.2.1"
    rl_ids: ["RL-245"]
    scanner_dims: []
    automation: manual
    profile_min: "kylin-redline-full"
    manual_note: "病毒/木马结论依赖防病毒软件扫描与结果存档；fileleak 仅在 ClamAV 等工具可用时输出辅助 WARN。"

  - clause_id: "4.3.1"
    rl_ids: ["RL-246"]
    scanner_dims: ["fileleak"]
    automation: partial
    profile_min: "kylin-redline-full"
    manual_note: "可检测 tcpdump、gdb、strace、nmap、gcc、JDK、调试脚本等交付包残留；组件用途和例外需人工确认。"

  - clause_id: "4.3.2"
    rl_ids: ["RL-143"]
    scanner_dims: ["url"]
    automation: partial
    profile_min: "kylin-redline-p0"
    manual_note: "可检测公网 IP、URL、域名和邮箱；是否已在界面或产品资料公开需人工对照资料。"

  - clause_id: "4.4.1"
    rl_ids: ["RL-247"]
    scanner_dims: ["component-info"]
    automation: partial
    profile_min: "kylin-redline-full"
    manual_note: "可检测 Docker、systemd、配置和监听信号中的 root 运行组合；进程是否对外服务或远程可访问需人工确认。"

  - clause_id: "5.1.1"
    rl_ids: ["RL-060", "RL-061", "RL-062", "RL-063"]
    scanner_dims: ["crypto"]
    automation: partial
    profile_min: "kylin-redline-p0"
    manual_note: "可检测 Base64 伪加密、XOR、移位、替换等信号；是否属于加解密场景需人工结合上下文确认。"

  - clause_id: "5.1.2"
    rl_ids: ["RL-120", "RL-121", "RL-122", "RL-123", "RL-124", "RL-125"]
    scanner_dims: []
    automation: manual
    profile_min: "kylin-redline-full"
    manual_note: "算法库是否通过认证、业界公认或公司评估认可依赖外部证明材料；scanner 仅可辅助识别库名和版本风险。"

  - clause_id: "5.1.3"
    rl_ids: ["RL-080", "RL-081", "RL-082", "RL-083", "RL-084"]
    scanner_dims: ["crypto"]
    automation: full
    profile_min: "kylin-redline-p0"

  - clause_id: "5.1.4"
    rl_ids: ["RL-001", "RL-002", "RL-003", "RL-004", "RL-005", "RL-020", "RL-021", "RL-022", "RL-040", "RL-041", "RL-042", "RL-043", "RL-044", "RL-100", "RL-101", "RL-102", "RL-103", "RL-104", "RL-105", "RL-106", "RL-107", "RL-108", "RL-109", "RL-110", "RL-111", "RL-112", "RL-113", "RL-114", "RL-115", "RL-116", "RL-117", "RL-118", "RL-119"]
    scanner_dims: ["crypto", "network"]
    automation: partial
    profile_min: "kylin-redline-p0"
    manual_note: "可检测不安全算法、协议和默认配置；升级兼容例外、行业标准例外、默认禁用和告警提示需人工确认。"

  - clause_id: "5.2.1"
    rl_ids: ["RL-217", "RL-248"]
    scanner_dims: ["secret", "crypto"]
    automation: partial
    profile_min: "kylin-redline-p0"
    manual_note: "可检测硬编码工作密钥和明文密钥信号；根密钥部分组件例外和访问控制需人工确认。"

  - clause_id: "6.1.1"
    rl_ids: ["RL-040", "RL-080", "RL-248"]
    scanner_dims: ["crypto", "secret"]
    automation: partial
    profile_min: "kylin-redline-p0"
    manual_note: "可检测明文凭据、弱哈希和 PBKDF2/盐值反模式；是否为认证凭据及性能例外需人工确认。"

  - clause_id: "6.1.2"
    rl_ids: ["RL-105", "RL-143"]
    scanner_dims: ["url", "network", "crypto"]
    automation: partial
    profile_min: "kylin-redline-p0"
    terminology_pending: true
    manual_note: "可检测敏感字段经 HTTP 或不安全协议传输；敏感数据范围、非信任网络边界和标准协议例外需人工确认。"

  - clause_id: "6.1.3"
    rl_ids: ["RL-249"]
    scanner_dims: []
    automation: manual
    profile_min: "kylin-redline-full"
    terminology_pending: true
    manual_note: "敏感数据访问是否具备认证、授权或加密机制依赖业务设计和运行时访问路径，自动 scanner 不硬判 FAIL。"

  - clause_id: "6.1.4"
    rl_ids: ["RL-218"]
    scanner_dims: ["secret"]
    automation: partial
    profile_min: "kylin-redline-full"
    manual_note: "可检测日志、调试信息、错误提示中的凭据输出 pattern；真实日志运行路径和脱敏策略需人工确认。"

  - clause_id: "7.1.1"
    rl_ids: ["RL-250"]
    scanner_dims: ["permission", "secret", "component-info"]
    automation: partial
    profile_min: "kylin-redline-full"
    manual_note: "口令文件访问控制可自动检测；口令复杂度 UI、防暴力破解、禁止明文显示、禁止拷出和改密流程属于人工检查清单。"

  - clause_id: "7.1.2"
    rl_ids: ["RL-251"]
    scanner_dims: []
    automation: manual
    profile_min: "kylin-redline-full"
    manual_note: "管理面审计日志覆盖范围、字段完整性、访问控制和禁止手动删除修改能力需要人工/运行时审查。"

  - clause_id: "7.1.3"
    rl_ids: ["RL-100", "RL-101", "RL-102", "RL-103", "RL-104", "RL-106", "RL-107", "RL-108", "RL-109", "RL-110", "RL-111", "RL-112", "RL-113", "RL-114", "RL-115", "RL-116", "RL-117", "RL-118", "RL-119"]
    scanner_dims: ["network", "crypto"]
    automation: partial
    profile_min: "kylin-redline-p0"
    manual_note: "可检测不安全协议配置；初始安装默认值、升级告警和资料指导需人工确认。"

  - clause_id: "7.1.4"
    rl_ids: ["RL-160", "RL-161", "RL-162", "RL-250"]
    scanner_dims: ["secret", "component-info"]
    automation: partial
    profile_min: "kylin-redline-p0"
    manual_note: "可检测硬编码缺省口令、空口令和 First login 信号；首次登录强制改密流程需人工/运行时确认。"

  - clause_id: "7.1.5"
    rl_ids: ["RL-252"]
    scanner_dims: []
    automation: manual
    profile_min: "kylin-redline-full"
    manual_note: "新建账号默认权限和最小角色分配属于权限模型审查，自动 scanner 不硬判 FAIL。"

  - clause_id: "8.1.1"
    rl_ids: ["RL-253"]
    scanner_dims: []
    automation: manual
    profile_min: "kylin-redline-full"
    terminology_pending: true
    manual_note: "产品通信矩阵属于发布资料完整性审计，自动 scanner 不读取或判定产品资料合规性。"

  - clause_id: "8.1.2"
    rl_ids: ["RL-254"]
    scanner_dims: []
    automation: manual
    profile_min: "kylin-redline-full"
    manual_note: "安全配置/加固指南属于产品发布资料审计，自动 scanner 不硬判 FAIL。"

  - clause_id: "8.1.3"
    rl_ids: ["RL-255"]
    scanner_dims: []
    automation: manual
    profile_min: "kylin-redline-full"
    manual_note: "缺省内置账号清单属于发布资料审计；component-info 可辅助发现账号信号但不能判定资料完整性。"

  - clause_id: "9.1.1"
    rl_ids: ["RL-140", "RL-141", "RL-142", "RL-143", "RL-144"]
    scanner_dims: ["component-info", "crypto", "network", "url"]
    automation: partial
    profile_min: "kylin-redline-full"
    manual_note: "可检测个人数据字段、明文存储/传输和日志信号；资料公开声明和保护机制完整性需人工确认。"

  - clause_id: "9.1.2"
    rl_ids: ["RL-256"]
    scanner_dims: []
    automation: manual
    profile_min: "kylin-redline-full"
    manual_note: "个人数据收集范围、使用目的和隐私声明一致性属于资料与流程审计，自动 scanner 不硬判 FAIL。"

  - clause_id: "9.1.3"
    rl_ids: ["RL-257"]
    scanner_dims: []
    automation: manual
    profile_min: "kylin-redline-full"
    manual_note: "移动终端升级知情可控需要界面、资料和运行时流程审查，自动 scanner 不硬判 FAIL。"

  - clause_id: "10.1.1"
    rl_ids: ["RL-220"]
    scanner_dims: ["integrity"]
    automation: partial
    profile_min: "kylin-redline-full"
    manual_note: "可检测 RPM/DEB 签名元数据和构建/安装脚本校验步骤；安装升级过程是否实际验证需人工或动态验证。"

  - clause_id: "11.1.1"
    rl_ids: ["RL-210"]
    scanner_dims: ["secure-coding"]
    automation: partial
    profile_min: "kylin-redline-full"
    manual_note: "可摄取或提示 SAST/semgrep/clang-tidy 结果；是否使用指定工具规则集并完成清理需人工确认。"

  - clause_id: "11.1.2"
    rl_ids: ["RL-211", "RL-212"]
    scanner_dims: ["secure-coding"]
    automation: partial
    profile_min: "kylin-redline-full"
    manual_note: "可检测不安全函数、安全函数宏重定义和错误封装 pattern；复杂宏解析歧义需人工裁决。"

  - clause_id: "11.2.1"
    rl_ids: ["RL-260"]
    scanner_dims: ["elf"]
    automation: partial
    profile_min: "kylin-redline-p0"
    manual_note: "ELF 侧可检测栈保护、NX、RELRO、PIE、BIND_NOW、RPATH 等；内核 ASLR=2 属运行时配置人工项。"

  - clause_id: "12.1.1"
    rl_ids: ["RL-202"]
    scanner_dims: ["dependency"]
    automation: partial
    profile_min: "kylin-redline-p0"
    manual_note: "可基于 manifest/SBOM 识别 EOM/EOL 和老旧组件；平台组件生命周期资料和最新版本策略需人工确认。"

  - clause_id: "12.1.2"
    rl_ids: ["RL-203"]
    scanner_dims: []
    automation: manual
    profile_min: "kylin-redline-full"
    manual_note: "漏洞处理标准和及时修复 SLA 属流程合规审计，自动 scanner 不硬判 FAIL。"

  - clause_id: "13.1.1"
    rl_ids: ["RL-230"]
    scanner_dims: ["content-compliance"]
    automation: partial
    profile_min: "kylin-redline-full"
    manual_note: "可检测明确禁词和错称；地图、图表、政治表述语境需人工审查，默认 WARN + needs_human。"
```
