# redline 条款切片：crypto

> 本文件由 `scripts/slice_redline_clauses.py` 从 `references/redline-mapping.md` 生成。
> 仅包含 `automation` 为 `full` 或 `partial` 且映射到当前维度的条款；manual 条款不注入 scanner。

```yaml
redline_clauses:
  - clause_id: 3.1.3
    rl_ids: ["RL-080", "RL-081", "RL-082", "RL-083", "RL-084", "RL-244"]
    automation: partial
    profile_min: redline-p0
    summary: >-
      Web应用程序的会话标识必须具备随机性；身份验证成功后，必须更换会话标识。
    manual_note: >-
      可检测弱随机数生成 session 标识和部分未 regenerate 信号；认证成功后是否必然换发会话标识需人工或动态测试确认。
  - clause_id: 5.1.1
    rl_ids: ["RL-060", "RL-061", "RL-062", "RL-063"]
    automation: partial
    profile_min: redline-p0
    summary: >-
      禁止使用私有加密算法。
    manual_note: >-
      可检测 Base64 伪加密、XOR、移位、替换等信号；是否属于加解密场景需人工结合上下文确认。
  - clause_id: 5.1.3
    rl_ids: ["RL-080", "RL-081", "RL-082", "RL-083", "RL-084"]
    automation: full
    profile_min: redline-p0
    summary: >-
      密码算法中使用到的随机数必须是密码学意义上的安全随机数。
  - clause_id: 5.1.4
    rl_ids: ["RL-001", "RL-002", "RL-003", "RL-004", "RL-005", "RL-020", "RL-021", "RL-022", "RL-040", "RL-041", "RL-042", "RL-043", "RL-044", "RL-100", "RL-101", "RL-102", "RL-103", "RL-104", "RL-105", "RL-106", "RL-107", "RL-108", "RL-109", "RL-110", "RL-111", "RL-112", "RL-113", "RL-114", "RL-115", "RL-116", "RL-117", "RL-118", "RL-119"]
    automation: partial
    profile_min: redline-p0
    summary: >-
      产品在初始安装需默认使用安全算法，禁止使用公司认定的不安全的加密密码算法，升级场景下可保持兼容，出于行业标准遵从的场景例外。
    manual_note: >-
      可检测不安全算法、协议和默认配置；升级兼容例外、行业标准例外、默认禁用和告警提示需人工确认。
  - clause_id: 5.2.1
    rl_ids: ["RL-217", "RL-248"]
    automation: partial
    profile_min: redline-p0
    summary: >-
      用于数据加解密的工作密钥不能硬编码在代码中，根密钥场景仅可对部分密钥组件进行硬编码。
    manual_note: >-
      可检测硬编码工作密钥和明文密钥信号；根密钥部分组件例外和访问控制需人工确认。
  - clause_id: 6.1.1
    rl_ids: ["RL-040", "RL-080", "RL-248"]
    automation: partial
    profile_min: redline-p0
    summary: >-
      禁止认证凭据明文存储在系统中，应该加密保护。在不需要还原明文的场景，必须使用不可逆算法加密。
    manual_note: >-
      可检测明文凭据、弱哈希和 PBKDF2/盐值反模式；是否为认证凭据及性能例外需人工确认。
  - clause_id: 6.1.2
    rl_ids: ["RL-105", "RL-143"]
    automation: partial
    profile_min: redline-p0
    summary: >-
      在非信任网络之间进行敏感数据的传输须采用安全传输通道或者加密后传输，有标准协议规定除外。
    manual_note: >-
      可检测敏感字段经 HTTP 或不安全协议传输；敏感数据范围、非信任网络边界和标准协议例外需人工确认。
    terminology_pending: true
  - clause_id: 7.1.3
    rl_ids: ["RL-100", "RL-101", "RL-102", "RL-103", "RL-104", "RL-106", "RL-107", "RL-108", "RL-109", "RL-110", "RL-111", "RL-112", "RL-113", "RL-114", "RL-115", "RL-116", "RL-117", "RL-118", "RL-119"]
    automation: partial
    profile_min: redline-p0
    summary: >-
      系统的管理平面和近端维护终端、网管维护终端间，初始安装必须默认使用安全协议，对于公司指定的已知不安全的协议应支持关闭。启用不安全协议须产生对应告警或用户提示。
    manual_note: >-
      可检测不安全协议配置；初始安装默认值、升级告警和资料指导需人工确认。
  - clause_id: 9.1.1
    rl_ids: ["RL-140", "RL-141", "RL-142", "RL-143", "RL-144"]
    automation: partial
    profile_min: redline-full
    summary: >-
      涉及个人数据的采集/处理的功能须提供安全保护机制（如认证、权限控制、日志记录等），并通过产品资料向客户公开。
    manual_note: >-
      可检测个人数据字段、明文存储/传输和日志信号；资料公开声明和保护机制完整性需人工确认。
```
