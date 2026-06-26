# checksec 工具使用指南

> 本文件指导 ELF 二进制安全编译扫描 Agent 如何正确使用 checksec 工具。

## 1. checksec 基本用法

### 1.1 检查单个文件

```bash
checksec --file=/path/to/binary
```

输出示例：

```text
RELRO           STACK CANARY      NX            PIE             RPATH      RUNPATH      Symbols         FORTIFY  Fortified  Fortifiable  FILE
Full RELRO      Canary found      NX enabled    PIE enabled     No RPATH   No RUNPATH   No Symbols      Yes      3          5            /usr/bin/ls
```

### 1.2 批量检查（按目录）

```bash
checksec --dir=/path/to/dir
```

### 1.3 JSON 输出（便于解析）

```bash
checksec --file=/path/to/binary --output=json
```

## 2. 各字段含义与判定规则

| 检查项 | PASS | WARN | FAIL | 建议参数 |
|--------|------|------|------|----------|
| RELRO（GOT 表保护） | `Full RELRO` | `Partial RELRO` | `No RELRO` | `-Wl,-z,relro,-z,now` |
| Stack Canary（栈保护） | `Canary found` | 不适用 | `No canary found` | `-fstack-protector-strong` |
| NX（堆栈不可执行） | `NX enabled` | 不适用 | `NX disabled` | `-Wl,-z,noexecstack` |
| PIE（地址无关） | `PIE enabled` 或 `DSO` | 不适用 | `No PIE` | `-fPIE -pie` 或 `-fPIC` |
| BIND_NOW（立即加载） | 包含 `BIND_NOW` | 不适用 | 不包含 `BIND_NOW` | `-Wl,-z,now` |
| RPATH/RUNPATH | `No RPATH` 且 `No RUNPATH` | 不适用 | 设置了 RPATH 或 RUNPATH | 移除 `--rpath` |
| Strip（符号信息） | `No Symbols` | 不适用 | `Symbols` | 发布包执行 `strip` |
| FORTIFY_SOURCE | `Fortify: Yes` 且 `Fortified > 0` | 部分函数加固 | `Fortify: No` 或 `Fortified = 0` | `-D_FORTIFY_SOURCE=2 -O2` |

## 3. readelf 降级方案

当 checksec 不可用时，使用 readelf 手动检查：

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

### 3.6 检查 FORTIFY_SOURCE

```bash
readelf -s /path/to/binary | grep "_chk@"
```

### 3.7 检查 Strip

```bash
file /path/to/binary | grep "stripped"
```
