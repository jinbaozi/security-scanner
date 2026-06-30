# 危险函数参考

> Secure-Coding Scanner 使用本文件识别高风险 API。命中后必须结合参数长度、输入来源和白名单判断。

## C/C++ 字符串与内存函数

| 函数 | 默认 severity | 风险 | 建议 |
|------|---------------|------|------|
| `gets` | high | 无边界输入 | 禁用，改用 `fgets` 并校验长度 |
| `strcpy` | high | 目标缓冲区可能溢出 | 使用长度受控接口并检查返回值 |
| `strcat` | high | 拼接溢出 | 使用长度受控接口并检查剩余空间 |
| `sprintf` | high | 格式化输出溢出 | 使用 `snprintf` 并检查返回值 |
| `vsprintf` | high | 变参格式化输出溢出 | 使用 `vsnprintf` |
| `scanf` / `sscanf` / `fscanf` | medium | 格式未限制宽度时溢出 | 为 `%s` 指定最大宽度 |
| `memcpy` / `memmove` | medium | 长度来源不可信时溢出 | 校验长度与目标缓冲区 |
| `strncpy` / `strncat` | medium | 截断或未 NUL 结尾 | 显式 NUL 结尾并检查返回 |

## 命令执行

| 函数 | 默认 severity | 风险 | 建议 |
|------|---------------|------|------|
| `system` | high | 命令注入 | 使用参数化 API，避免 shell |
| `popen` | high | 命令注入和输出处理风险 | 使用 execve 类接口并固定参数 |
| `execl` / `execv` / `execvp` | medium | 参数可控时风险高 | 固定可执行路径和参数白名单 |
| `ShellExecute` | medium | Windows 命令/文件打开风险 | 固定动词、路径和参数 |

## 判定提示

- 测试样例、第三方源码和生成代码优先降级或跳过。
- 仅出现函数名不等于问题；必须保留调用证据和上下文。
- 命中 `strcpy_s`、`memcpy_s` 等安全函数时，应继续检查是否被宏降级或忽略返回值。
