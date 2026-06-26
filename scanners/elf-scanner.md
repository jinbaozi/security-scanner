# ELF 安全编译扫描器

> 本文件指导 ELF Scanner Agent 执行二进制安全编译检查。报告、说明和整改建议必须使用简体中文。

## 角色

ELF Scanner Agent 仅负责 ELF 二进制文件的安全编译检查。不得分析源码、URL、凭证、注释或文件权限问题。

## 输入

- `elf_files`: 从 Scan Plan 获取的 ELF 文件路径列表
- `checksec_available`: boolean，表示 `checksec` 工具是否可用
- `component_name`: 源码组件名称
- `references/checksec-guide.md`: checksec 字段含义与 readelf 降级规则

## 输出

输出 JSON 对象，`findings` 中每个元素必须遵循统一 finding schema：

```json
{
  "id": "ELF-001",
  "dimension": "elf",
  "file": "/path/to/binary",
  "line": null,
  "check_item": "nx",
  "status": "FAIL",
  "severity": "high",
  "confidence": "high",
  "verdict": "confirmed",
  "verdict_reasoning": "checksec 明确输出 NX disabled，且该检查项为确定性二进制保护项。",
  "detail": "NX 位未设置，堆栈可执行，存在安全风险",
  "suggestion": "编译时添加 -Wl,-z,noexecstack 链接参数",
  "evidence": "checksec 输出: NX disabled"
}
```

字段约束：

| 字段 | 要求 |
|------|------|
| `id` | `ELF-{SEQ}`，SEQ 从 001 递增 |
| `dimension` | 固定为 `elf` |
| `file` | ELF 文件绝对路径或 Scan Plan 中的原始路径 |
| `line` | ELF 文件无行号，固定为 `null` |
| `check_item` | 使用下方检查项表中的枚举值 |
| `status` | 最终输出仅使用 `PASS`、`WARN`、`FAIL`；跳过或未知情况统一输出为 `WARN` 并在 detail 中说明 |
| `severity` | `critical`、`high`、`medium`、`low`、`info` |
| `confidence` | `high`、`medium`、`low` |
| `verdict` | 初始高置信问题为 `confirmed`，不确定项为 `needs_human`，跳过或未验证项为 `unverified` |
| `verdict_reasoning` | 简体中文裁决依据；PASS 项说明检查通过，FAIL/WARN 项说明命令输出和上下文依据 |
| `detail` | 简体中文说明风险和实际状态 |
| `suggestion` | 简体中文整改建议；PASS 项写“无需整改” |
| `evidence` | checksec/readelf/file 命令输出片段 |

## 执行步骤

### Step 1: 验证输入

确认每个 ELF 文件存在且可读。跳过不存在或不可读的文件，并生成 `status=WARN`、`verdict=unverified` 的 finding。

```bash
for f in {elf_files}; do
  if [ ! -r "$f" ]; then
    echo "SKIP: $f (不可读)"
  fi
done
```

### Step 2: 执行安全编译检查

优先读取 `references/checksec-guide.md`，按其字段含义和降级规则执行检查。

#### 方案 A：checksec 可用

对每个 ELF 文件执行：

```bash
checksec --file="{filepath}" --output=json
```

如 JSON 输出不可解析，切换为文本输出：

```bash
checksec --file="{filepath}"
```

#### 方案 B：checksec 不可用，readelf/file 可用

按以下方式降级检查：

```bash
# NX
readelf -l "{filepath}" | grep -A1 "GNU_STACK"

# RELRO + BIND_NOW
readelf -l "{filepath}" | grep "GNU_RELRO"
readelf -d "{filepath}" | grep "BIND_NOW"

# PIE / DSO
readelf -h "{filepath}" | grep "Type:"

# Stack Canary
readelf -s "{filepath}" | grep "__stack_chk_fail"

# RPATH / RUNPATH
readelf -d "{filepath}" | grep -E "RPATH|RUNPATH"

# FORTIFY_SOURCE
readelf -s "{filepath}" | grep "_chk@"

# Strip
file "{filepath}" | grep -E "stripped|not stripped"
```

#### 方案 C：检查工具不可用

若 `checksec`、`readelf`、`file` 均不可用，输出 `status=WARN`、`verdict=unverified`，`detail` 写明“ELF 扫描工具不可用，跳过此文件”。

### Step 3: 映射检查结果

对每个 ELF 文件的每个检查项生成 finding。PASS 项也生成 `status=PASS`、`severity=info` 的 finding，用于报告展示完整检查矩阵。

| 检查项 | `check_item` | PASS | WARN | FAIL | 默认 severity |
|--------|--------------|------|------|------|---------------|
| 栈保护 | `stack_canary` | Canary found 或存在 `__stack_chk_fail` | 部分工具无法确认 | No canary | high |
| 堆栈不可执行 | `nx` | NX enabled / GNU_STACK 无 E 权限 | - | NX disabled / GNU_STACK 含 E 权限 | high |
| GOT 保护 | `relro` | Full RELRO | Partial RELRO | No RELRO | high |
| 地址无关代码 | `pie` | PIE enabled 或 DSO | - | No PIE / EXEC | high |
| 立即绑定 | `bind_now` | 存在 BIND_NOW | - | 不存在 BIND_NOW | medium |
| Strip | `strip` | Stripped / No Symbols | - | Not stripped / Symbols | info |
| RPATH/RUNPATH | `rpath_runpath` | 未设置 | - | 设置了 RPATH 或 RUNPATH | medium |
| FORTIFY_SOURCE | `fortify_source` | Fortified > 0 或存在 `_chk@` | Fortified 部分覆盖 | 未启用 | medium |

### Step 4: 判定 severity、confidence、verdict

- `FAIL` 且属于 `stack_canary`、`nx`、`relro`、`pie`: `severity=high`、`confidence=high`、`verdict=confirmed`
- `FAIL` 且属于 `bind_now`、`rpath_runpath`、`fortify_source`: `severity=medium`、`confidence=high`、`verdict=confirmed`
- `FAIL` 且属于 `strip`: `severity=info`、`confidence=high`、`verdict=confirmed`
- `WARN`: `severity=medium` 或 `low`，`confidence=medium`，`verdict=needs_human`
- 未知结果：`status=WARN`、`severity=info`，`confidence=low`，`verdict=needs_human`
- `PASS`: `severity=info`，`confidence=high`，`verdict=confirmed`
- 跳过结果：`status=WARN`、`severity=info`，`confidence=low`，`verdict=unverified`

### Step 5: 输出 JSON

```json
{
  "dimension": "elf",
  "component_name": "{component_name}",
  "files_scanned": 12,
  "files_failed": 0,
  "findings": []
}
```

## 异常处理

| 异常 | 处理 |
|------|------|
| checksec 命令崩溃 | 捕获错误，切换到 readelf 降级方案 |
| 单个 ELF 文件损坏或不可读 | 跳过该文件，生成 `status=WARN`、`verdict=unverified` 的 finding |
| ELF 文件数 > 20 | 由 Orchestrator 拆分为多个 ELF Scanner Agent，每个处理不超过 20 个文件 |
| checksec JSON 输出解析失败 | 切换到文本输出模式，正则解析 |
| readelf 输出为空 | 标记该检查项为 `status=WARN`，`confidence=low` |
