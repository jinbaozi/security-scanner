# ELF 安全编译扫描器

> 本文件指导 ELF Scanner Agent 执行二进制安全编译检查。报告、说明和整改建议必须使用简体中文。不得向用户回显已读 reference 全文或完整文件清单。

## 有界工具输出（强制）

模式搜索必须调用 `$SKILL_ROOT/scripts/safe_grep.py` 并读取其 JSON；下文裸 `grep` 仅表示检测规则，禁止直接执行。默认最多保留 200 条样本、32 KiB JSON，完整计数保留在文件中且终端只输出一行。单维 finding 上限 200；超限按严重度和 file/check_item 聚合，audit_log 必须记录 `truncated_count`，原始命中写 evidence 文件且不得回显。

## 角色

ELF Scanner Agent 仅负责 ELF 二进制文件的安全编译检查。不得分析源码、URL、凭证、注释或文件权限问题。

## 输入

- `elf_files`: 从 Scan Plan 获取的 ELF 文件路径列表
- `config_files` / `build_files`（可选）：构建脚本、安装脚本、sysctl 配置片段，用于弱检 ASLR 加固配置
- `elf_probe_json`: `scripts/elf_hardening_probe.py` 生成的结构化工具执行证据；若尚未生成，本 scanner 必须先调用 probe
- `component_name`: 源码组件名称
- `references/checksec-guide.md`: checksec 字段含义与 readelf 降级规则
- `references/redline-clauses.md`: elf 维度 redline 条款切片。

## 输出

输出 JSON 对象，`findings` 中每个元素必须符合统一 finding schema（Orchestrator 注入 finding-schema；字段定义见该文件）。最小示例如下：

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
  "evidence": "checksec 输出: NX disabled",
  "redline_clause": "11.2.1",
  "rl_ids": ["RL-260"]
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
| `redline_clause` | 命中的 redline 条款编号；无映射时为 `null` |
| `rl_ids` | 命中的 RL-ID 数组；无映射时为 `[]` |

Redline 追溯约束：WARN/FAIL finding 必须优先从本维度 `references/redline-clauses.md` 选择 `redline_clause` 与 `rl_ids`；不得输出本维度 `references/redline-clauses.md` 未定义的条款组合。

> redline 11.2.1 的二进制侧由 PIE、NX、RELRO、Canary、BIND_NOW、FORTIFY_SOURCE 等安全编译项覆盖。内核 ASLR（如 `/proc/sys/kernel/randomize_va_space=2`）属于运行时/系统加固配置，本 scanner 不新增 `aslr` check_item；仅对构建或安装脚本中的明显弱化配置输出 WARN。

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

### Step 2: 执行确定性安全编译探测

ELF Scanner 不得直接拼接或猜测 `checksec` 参数。必须调用确定性适配器，并把完整 JSON 写入 `security-reports/`：

```bash
python3 "$SKILL_ROOT/scripts/elf_hardening_probe.py" \
  --list-file "$REPORT_ROOT/recon/elf-files.txt" \
  --output-json "$REPORT_ROOT/elf-probe-{component_name}.json" \
  --batch-size 20 \
  --checkpoint \
  --resume
```

多个 ELF 文件可重复传入 `--file`，或使用 `--list-file PATH`。每个 batch 完成后必须原子写 checkpoint；Pi 中断后使用 `--resume` 跳过已有 `results[].file`。probe stdout 只允许输出一行摘要；scanner 必须读取 `--output-json` 指向的文件作为唯一工具证据来源。

probe JSON 必须包含并保留到 scanner audit_log：

- `status`: `ready | degraded | blocked`
- `checksec_state`
- `selected_mode`（摘要字段）
- `fallback_used`
- `fallback_reason`
- `unavailable_proof`
- `tool_invocations`
- `results[]`

`checksec_state` 只表达全局工具能力探测结果；`selected_mode 仅为摘要字段`，多文件扫描的准确模式以 `results[].mode` 为准。每个 `results[]` 必须保留自己的 `mode`、`parser`、`status`、`failure_reason` 和 `tool_invocation_refs`。

工具降级门禁：

- `checksec_state=available` 且 `results[].status=ready`、`results[].source=checksec` 时，按 `results[].checks` 映射 finding。
- `fallback_used=true` 仅在存在 confirmed unavailable proof 时可接受：全局 `checksec_state=confirmed_unavailable` 且顶层存在 `unavailable_proof`，或单文件 checksec 运行依赖错误且该 `results[]` 存在 `unavailable_proof`。此时 `readelf` / `file` 结果为降级证据。
- `invocation_error`、`parse_error`、参数不兼容、usage error 或 probe `status=blocked` 时，不得改用 readelf 兜底；必须输出 blocked/unverified 证据，要求修复工具调用或安装正确版本。
- 单个 ELF 不存在或不可读时，只为该文件输出 `verdict=unverified`，不得污染全局 `checksec_state`。

### Step 3: 映射检查结果

读取 `elf_probe_json.results[]`，对每个 ELF 文件的每个检查项生成 finding。PASS 项也生成 `status=PASS`、`severity=info` 的 finding，用于报告展示完整检查矩阵。

映射规则：

- `results[].status=ready`：使用 `source=checksec` 的字段，`evidence` 引用 `tool_invocations` 中的 checksec 命令、exit code 和 parser。
- `results[].status=degraded`：仅当存在顶层 `unavailable_proof` 或该结果自身的 `unavailable_proof`，且 `fallback_reason=checksec_confirmed_unavailable` 时使用 readelf/file 结果；`confidence` 最高为 `medium`，`evidence` 必须写明降级原因。
- `results[].status=blocked`：不生成看似通过的 PASS；输出 `status=WARN`、`verdict=unverified` 的工具阻断 finding，`detail` 写明 `failure_reason`。
- `results[].status=unverified`：输出 `status=WARN`、`verdict=unverified` 的文件级 finding。
- readelf 输出为空或对应子命令失败时，该检查项输出 `unknown/unverified`，不得推导 PASS/FAIL。

检查项分为两类：
- **红线项**：发现问题时 `status=FAIL`，报告中标记为 **Error**，必须整改。包括：RELRO、Canary、NX、PIE、RPATH、BIND_NOW、Strip、FORTIFY_SOURCE。
- **可选项**（Trapv、stack-check）：当前标准 checksec.sh 不覆盖，**不做检查**。如需启用，需使用支持扩展检查的 checksec 版本或通过构建脚本验证。

| 类别 | 检查项 | `check_item` | PASS | WARN | FAIL | 默认 severity |
|------|--------|--------------|------|------|------|---------------|
| 红线项 | 栈保护 | `stack_canary` | Canary found 或存在 `__stack_chk_fail` | 部分工具无法确认 | No canary | high |
| 红线项 | 堆栈不可执行 | `nx` | NX enabled / GNU_STACK 无 E 权限 | - | NX disabled / GNU_STACK 含 E 权限 | high |
| 红线项 | GOT 保护 | `relro` | Full RELRO | Partial RELRO | No RELRO | high |
| 红线项 | 地址无关代码 | `pie` | PIE enabled 或 DSO | - | No PIE / EXEC | high |
| 红线项 | 立即绑定 | `bind_now` | 存在 BIND_NOW | - | 不存在 BIND_NOW | medium |
| 红线项 | 符号剥离 | `strip` | Stripped / No Symbols | - | Not stripped / Symbols | info |
| 红线项 | RPATH/RUNPATH | `rpath_runpath` | 未设置 | - | 设置了 RPATH 或 RUNPATH | medium |
| 红线项 | FORTIFY_SOURCE | `fortify_source` | Fortified > 0 或存在 `_chk@` | Fortified 部分覆盖 | 未启用 | medium |
| 不检查 | 整数溢出防护 | `trapv` | - | - | - | - |
| 不检查 | 栈溢出检测 | `stack_check` | - | - | - | - |

> trapv 和 stack-check 行仅用于完整性说明，实际不会生成 finding。报告不包含这两项。

### Step 3b: 加固脚本弱检（不新增 ASLR check_item）

对 `config_files` / `build_files` 中的 sysctl、安装脚本和容器启动脚本执行弱检：

```bash
grep -rnE "randomize_va_space\s*=\s*[01]\|kernel\.randomize_va_space\s*=\s*[01]\|echo\s+[01]\s*>\s*/proc/sys/kernel/randomize_va_space" {config_and_build_files}
```

命中时输出 `check_item=pie` 的 `WARN` finding（不是 `FAIL`，也不新增 `aslr` check_item），`detail` 说明“脚本疑似关闭或弱化内核 ASLR；PIE 已覆盖二进制侧，运行时加固需人工确认”，`redline_clause=11.2.1`。

### Step 4: 判定 severity、confidence、verdict

红线项 FAIL 统一按 Error 级别上报，根据问题严重程度区分 severity：

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
| probe `checksec_state=confirmed_unavailable` 且含 `unavailable_proof` | 允许使用 readelf/file 降级结果，并在 evidence 中引用 proof |
| probe `checksec_state=invocation_error` 或 `parse_error` | 不得 readelf 降级；标记 blocked/unverified 并要求修复工具调用或 parser |
| probe `status=blocked` | 不进入正常 PASS/FAIL 矩阵；输出工具阻断 finding |
| 单个 ELF 文件损坏或不可读 | 跳过该文件，生成 `status=WARN`、`verdict=unverified` 的 finding |
| ELF 文件数 > 20 | 由 Orchestrator 拆分为多个 ELF Scanner Agent，每个处理不超过 20 个文件 |
| checksec JSON 输出解析失败 | 由 probe 自动尝试其他 checksec JSON 模式和文本模式；文本也不可解析时 blocked |
| readelf 输出为空或对应子命令失败 | 仅在 confirmed unavailable 降级路径中将对应检查项标记为 `unknown/unverified`，映射 finding 时使用 `status=WARN`、`confidence=low`，不得推导 PASS/FAIL |
