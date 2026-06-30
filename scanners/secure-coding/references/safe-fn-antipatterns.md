# 安全函数失效反模式

> 本文件维护 11.1.2 相关的安全函数失效宏、错误封装和构建配置反模式。

## 反模式 1：宏降级

| Pattern | 风险 | 判定 |
|---------|------|------|
| `#define strcpy_s strcpy` | 安全函数被替换为不安全函数 | `FAIL/high` |
| `#define memcpy_s memcpy` | 丢失目标长度和返回值检查 | `FAIL/high` |
| `#define sprintf_s sprintf` | 格式化输出溢出 | `FAIL/high` |
| `#define strncpy_s strncpy` | 截断/结尾语义不一致 | `WARN/medium` |

## 反模式 2：关闭边界检查

| Pattern | 风险 | 判定 |
|---------|------|------|
| `#define _FORTIFY_SOURCE 0` | 关闭 glibc Fortify | `FAIL/high` |
| `-U_FORTIFY_SOURCE` | 构建参数移除 Fortify | `WARN/medium` |
| `-D_FORTIFY_SOURCE=0` | 构建参数关闭 Fortify | `FAIL/high` |

## 反模式 3：错误封装

| Pattern | 风险 | 判定 |
|---------|------|------|
| wrapper 固定长度为 `sizeof(src)` | 目标缓冲区长度错误 | `WARN/medium` |
| 忽略 `strcpy_s` / `memcpy_s` 返回值 | 失败后继续使用未定义数据 | `WARN/medium` |
| 捕获错误但只记录日志不返回 | 调用方误以为操作成功 | `WARN/medium` |

## 输出建议

- 明确指出宏定义或 wrapper 位置。
- evidence 同时包含宏定义和至少一个调用点时，confidence 可提升为 high。
- 无调用点时先输出 WARN，不硬判实际漏洞。
