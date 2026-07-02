# checksec 字段与降级语义指南

> 本文件说明 checksec 字段含义和 readelf 降级语义。
> ELF Scanner Agent 不直接调用 checksec；必须通过 `scripts/elf_hardening_probe.py` 生成结构化 JSON 后再映射 finding。
>
> 上游地址：<https://github.com/slimm609/checksec>

## 1. probe 内部 checksec 模式

probe 会先验证 checksec 是否可执行，再按顺序尝试以下模式：

- `format_json`：支持 `--format=json` 的版本。
- `output_json`：支持 `--output=json` 的版本。
- `text`：JSON 模式不可解析时，回到 checksec 文本输出解析。

ELF Scanner 只消费 probe JSON，不直接消费下方示例输出。文本输出示例：

```text
RELRO           STACK CANARY      NX            PIE             RPATH      RUNPATH      Symbols         FORTIFY  Fortified  Fortifiable  FILE
Full RELRO      Canary found      NX enabled    PIE enabled     No RPATH   No RUNPATH   No Symbols      Yes      3          5            /usr/bin/ls
```

如果 JSON 模式失败但文本模式可解析，仍视为 `checksec_state=available`。如果参数错误、usage error 或所有 parser 都失败，则 probe 必须返回 `blocked` / `invocation_error` / `parse_error`，不得进入 readelf 降级。`checksec --help` 成功只代表工具初步可执行；若单文件 checksec 调用暴露共享库缺失、bad interpreter、permission denied、cannot execute 等运行依赖错误，应分类为 `broken` 并生成 `unavailable_proof`，可按 confirmed unavailable proof 进入 readelf/file 降级。

## 2. 各字段含义与判定规则

> 标准 checksec.sh 覆盖以下 8 项检查：RELRO、Stack Canary、NX、PIE、BIND_NOW、RPATH/RUNPATH、Strip、FORTIFY_SOURCE。
> `trapv`（整数溢出防护）和 `stack-check`（栈溢出检测）不在标准输出中，本扫描器不做检查。

| 检查项 | PASS | WARN | FAIL | 建议参数 |
|--------|------|------|------|----------|
| RELRO（GOT 表保护） | `Full RELRO` | `Partial RELRO` | `No RELRO` | `-Wl,-z,relro,-z,now` |
| Stack Canary（栈保护） | `Canary found` | 不适用 | `No canary found` | `-fstack-protector-strong` |
| NX（堆栈不可执行） | `NX enabled` | 不适用 | `NX disabled` | `-Wl,-z,noexecstack` |
| PIE（地址无关） | `PIE enabled` 或 `DSO` | 不适用 | `No PIE` | `-fPIE -pie` 或 `-fPIC` |
| BIND_NOW（立即加载） | 包含 `BIND_NOW` | 不适用 | 不包含 `BIND_NOW` | `-Wl,-z,now` |
| RPATH/RUNPATH | `No RPATH` 且 `No RUNPATH` | 不适用 | 设置了 RPATH 或 RUNPATH | 移除 `--rpath`，避免发布包携带可控库搜索路径 |
| Strip（符号信息） | `No Symbols` | 不适用 | `Symbols` | 发布包执行 `strip` |
| FORTIFY_SOURCE | `Fortify: Yes` 且 `Fortified > 0` | 部分函数加固 | `Fortify: No` 或 `Fortified = 0` | `-D_FORTIFY_SOURCE=2 -O2` |

## 3. readelf 降级方案

仅当 probe 已证明 `checksec_state=confirmed_unavailable` 且包含顶层 `unavailable_proof`，或单文件结果包含 `broken/missing` 的 `unavailable_proof` 时，才允许使用 readelf/file 手动检查。

readelf/file 每个子命令必须独立记录状态。只有对应命令成功且输出非空时，才可推导该检查项的 PASS/FAIL；子命令失败或输出为空时，该检查项必须为 `unknown/unverified`，不得推导 `No RELRO`、`No canary` 或 `Not fortified` 等负面结论。顶层 `status=degraded` 只表示进入 confirmed unavailable 降级路径，不表示所有检查项都有可判定证据。

### 3.1 检查 NX

```bash
readelf -l /path/to/binary | grep -A1 "GNU_STACK"
# 输出包含 "RWE" → NX 未启用（FAIL）
# 输出包含 "RW" 但无 "E" → NX 已启用（PASS）
```

### 3.2 检查 RELRO

```bash
readelf -l /path/to/binary | grep "GNU_RELRO"
readelf -d /path/to/binary | grep "BIND_NOW"
```

存在 `GNU_RELRO` 且存在 `BIND_NOW` 为 Full RELRO；仅存在 `GNU_RELRO` 为 Partial RELRO；两者均不存在为 No RELRO。

### 3.3 检查 PIE

```bash
readelf -h /path/to/binary | grep "Type:"
# "DYN" → PIE enabled 或 DSO
# "EXEC" → No PIE (FAIL)
```

### 3.4 检查 Stack Canary

```bash
readelf -s /path/to/binary | grep "__stack_chk_fail"
```

### 3.5 检查 RPATH/RUNPATH

```bash
readelf -d /path/to/binary | grep -E "RPATH|RUNPATH"
```

判定说明：

- `RPATH` 和 `RUNPATH` 都表示二进制携带运行时库搜索路径，发布包中通常应移除。
- 构建参数 `-Wl,--disable-new-dtags` 会让链接器生成旧式 `DT_RPATH`，优先级高于 `LD_LIBRARY_PATH`，风险通常高于 `RUNPATH`。
- 仅出现 `RUNPATH` 也不能直接 PASS；若路径指向 `$ORIGIN`、相对路径、临时目录、可写目录或交付包外路径，应输出 `FAIL/WARN` 并要求人工确认。
- 修复建议优先移除 rpath/runpath；确需使用 `$ORIGIN` 时，应限制到只读、随包交付且不可被普通用户写入的目录。

### 3.6 检查 FORTIFY_SOURCE

```bash
readelf -s /path/to/binary | grep "_chk@"
```

### 3.7 检查 Strip

```bash
file /path/to/binary | grep "stripped"
```
