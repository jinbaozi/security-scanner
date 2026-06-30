# Component Info: security-scanner

> 本文件是 security-scanner 自身的组件基础信息档案。目的是示范模板格式。
> 严格按照 9 字段 + 红线判定填写；本组件当前提供 13 个 scanner 维度。

## 基本信息

- **组件名称**: security-scanner
- **组件版本**: 1.0.0
- **扫描日期**: 2026-06-30

## 9 字段档案

| 字段 | 值 | 标签 | 备注 |
|------|-----|------|------|
| 1. 架构类型 | 不涉及 | MISSING | security-scanner 是 SKILL 指令包，不是可执行服务 |
| 2. 通信协议 | 不涉及 | MISSING | security-scanner 不实现网络通信 |
| 3a. 对称算法 | 不涉及 | MISSING | security-scanner 不实现密码学 |
| 3b. 非对称算法 | 不涉及 | MISSING | security-scanner 不实现密码学 |
| 3c. Hash 算法 | 不涉及 | MISSING | security-scanner 不实现密码学 |
| 3d. 自定义算法 | 不涉及 | MISSING | security-scanner 不实现密码学 |
| 4. 伪加密 | 不涉及 | MISSING | security-scanner 不实现密码学 |
| 5. 随机数 | 不涉及 | MISSING | security-scanner 不使用随机数 |
| 6. 默认账号 | 无 | MISSING | security-scanner 不提供用户系统 |
| 7. 端口 | 无 | MISSING | security-scanner 不监听端口 |
| 8. 个人数据 | 无 | MISSING | security-scanner 不采集任何用户数据 |
| 9. 是否需 root 启动 | 否 | AUTO | security-scanner 由 AI agent 加载执行，普通用户权限即可 |

## 红线合规判定

| 红线 | 状态 | 说明 |
|------|------|------|
| 红线 1：严禁私有或伪加密 | 不适用 | security-scanner 不实现密码学 |
| 红线 2：禁止不安全算法/协议 | 不适用 | security-scanner 不实现算法/协议 |
| 红线 3：密码算法随机数安全 | 不适用 | security-scanner 不使用随机数 |
| 红线 4：所有命令/参数/端口文档化 | PASS | security-scanner 的所有 markdown 文件即为完整文档；无未公开命令/参数/端口 |
| 红线 5：默认账号与个人数据合规 | PASS | 无默认账号，无个人数据采集 |

## 字段完整性自检

- [x] 9 个字段全部填写
- [x] 每字段含 value + label + 备注
- [x] 5 红线全部判定
- [x] 文档化：本档案文件本身即为文档

## 反向证据

| 字段 | 已搜索 | 命中 |
|------|--------|------|
| 端口 | `bind(`, `listen `, `port:`, `server.port` | 0 |
| 个人数据 | `phone`, `id_card`, `email` | 0 |
| 默认账号 | `admin`, `root` 紧邻 password/secret | 0 |
| 随机数 | `RAND_bytes`, `Math.random` | 0 |
| 算法 | `AES`, `DES`, `MD5`, `SHA-` | 0 |
| 不安全协议 | `SSLv3`, `TLSv1.0`, `Telnet` | 0 |