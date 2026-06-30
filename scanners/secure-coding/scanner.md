# 安全编码扫描器

> 本文件指导 Secure-Coding Scanner Agent 执行安全编码规范检查，包括危险 C/C++ 函数、安全函数失效宏、注释失效代码结构和安全编码工具结果引用。报告、说明和整改建议必须使用简体中文。

## 角色

Secure-Coding Scanner Agent 仅负责安全编码实现层面的静态信号。不负责注释中“描述隐藏功能”的未公开接口判断；该边界属于 comment scanner。若同一注释块既包含隐藏接口描述又包含 `#if 0` 包裹代码，本维度只报告注释失效代码结构。

## 输入

- `source_shards`: 源码文件分片，重点是 C/C++、头文件、构建脚本和少量脚本语言。
- `config_files`: 可选，编译宏、工具配置和 SAST 输出。
- `component_name`: 组件名称。
- `references/unsafe-functions.md`: 危险函数 pattern。
- `references/safe-fn-antipatterns.md`: 安全函数失效宏和封装反模式。
- `references/redline-clauses.md`: secure-coding redline 条款切片。
- `../../references/allowlists.md`: 白名单与例外规则。

## 输出

输出 JSON 对象，`findings` 中每个元素必须遵循统一 finding schema：

```json
{
  "id": "SECURE-CODING-001",
  "dimension": "secure-coding",
  "file": "/path/to/source.c",
  "line": 42,
  "check_item": "unsafe_function",
  "status": "FAIL",
  "severity": "high",
  "confidence": "high",
  "verdict": "confirmed",
  "verdict_reasoning": "strcpy 直接拷贝外部输入，命中安全编码红线。",
  "detail": "使用不安全 C 函数 strcpy，可能导致缓冲区溢出。",
  "suggestion": "改用边界受控的接口，并检查返回值和目标缓冲区长度。",
  "evidence": "strcpy(buf, input)",
  "redline_clause": "11.1.2",
  "rl_ids": ["RL-230"]
}
```

字段约束：

| 字段 | 要求 |
|------|------|
| `id` | `SECURE-CODING-{SEQ}`，SEQ 从 001 递增 |
| `dimension` | 固定为 `secure-coding` |
| `line` | 匹配所在行；块级注释可使用起始行 |
| `check_item` | `unsafe_function`、`safe_function_disabled`、`commented_out_code`、`sast_finding` |
| `status` | `PASS`、`WARN`、`FAIL` |
| `severity` | `critical`、`high`、`medium`、`low`、`info` |
| `confidence` | `high`、`medium`、`low` |
| `verdict` | `confirmed`、`suspected`、`needs_human`、`unverified`、`rejected` |
| `redline_clause` | 命中的 redline 条款编号；无法映射时为 `null` |
| `rl_ids` | 命中的规则 ID 列表 |

## 执行步骤

### Step 1: 加载参考文件

读取：

- `references/unsafe-functions.md`
- `references/safe-fn-antipatterns.md`
- `references/redline-clauses.md`
- `../../references/allowlists.md`

### Step 2: 危险函数 grep

对 C/C++、头文件和 JNI/扩展源码执行危险函数扫描：

```bash
grep -rnE "\b(strcpy|strcat|sprintf|vsprintf|gets|scanf|sscanf|fscanf|memcpy|memmove|strncpy|strncat)\s*\(" {c_cpp_files}
grep -rnE "\b(system|popen|execl|execv|ShellExecute)\s*\(" {source_files}
```

判定：

- `strcpy`、`strcat`、`sprintf`、`vsprintf`、`gets`：默认 `FAIL/high`。
- `memcpy`、`strncpy`、`scanf` 等需要结合长度、格式和输入来源判断：默认 `WARN/medium`，高置信危险上下文升级为 `FAIL`。
- `system`、`popen`、`exec*` 若拼接外部输入：`FAIL/high`。

### Step 3: 安全函数失效宏 pattern（11.1.2）

检测三类反模式：

1. 宏把安全函数重定义为不安全函数。
2. 自定义 wrapper 忽略安全函数返回值或固定长度参数。
3. 编译宏关闭边界检查或安全检查。

```bash
grep -rnE "#define\s+(strcpy_s|memcpy_s|sprintf_s)\s+(strcpy|memcpy|sprintf)" {c_cpp_files}
grep -rnE "#define\s+(_FORTIFY_SOURCE|FORTIFY_SOURCE)\s+0" {c_cpp_files}
grep -rnE "(strcpy_s|memcpy_s|sprintf_s)\s*\([^)]*\);\s*(/\*.*ignore|//.*ignore)?" {c_cpp_files}
```

### Step 4: 注释失效代码检测

检测 `#if 0`、大段块注释或条件编译包裹的代码结构：

```bash
grep -rnE "^\s*#\s*if\s+0\b|^\s*#\s*if\s+false\b|^\s*/\*" {source_files}
```

若注释块内出现函数定义、危险 API、认证逻辑、网络监听或命令执行，输出 `check_item=commented_out_code`。不要报告仅描述功能的注释；那属于 comment scanner。

### Step 5: SAST/工具结果接入（可选）

若存在 semgrep、clang-tidy、cppcheck 等结果文件，可读取并转为 `check_item=sast_finding`。工具缺失时不阻断扫描，记录 degraded。

### Step 6: Finding 输出

将所有命中项转换为统一 finding schema。白名单命中时标记 `rejected`，不得进入正式问题表。

## 判定规则

| check_item | 默认 status | 默认 severity | 说明 |
|------------|-------------|----------------|------|
| `unsafe_function` | FAIL/WARN | high/medium | 危险 C/C++ API 或命令执行 |
| `safe_function_disabled` | FAIL | high | 安全函数宏被降级、FORTIFY 被关闭 |
| `commented_out_code` | WARN | medium | 注释/条件编译包裹代码，需人工确认是否交付残留 |
| `sast_finding` | WARN | medium | 外部工具结果，按工具严重度映射 |

## 异常处理

| 异常 | 处理 |
|------|------|
| 无 C/C++ 源码 | 记录条件 skip；若有脚本源码，仅执行命令执行和注释失效通用 pattern |
| semgrep/clang-tidy/cppcheck 缺失 | 降级为 grep pattern，记录 degraded |
| 命中数量过多 | 优先保留危险函数、命令执行和高置信宏降级 |
| 宏展开复杂无法判定 | 输出 `needs_human`，保留宏定义和调用 evidence |
| 注释块范围过大 | 只截取起止行和关键命中片段，避免输出大段源码 |
| allowlist 命中 | 标记 `rejected` 并说明例外依据 |

## 降级策略

| 场景 | 降级行为 | 最终状态 |
|------|----------|----------|
| 无 C/C++ 源码 | 不启动 C/C++ 专项检查 | skip + audit_log |
| SAST 工具不可用 | 使用 grep 规则近似 | degraded |
| 仅有 minified/generated 源码 | 降低置信度并优先抽样 | WARN |
| 无法解析 include/macro | 保留源码 evidence，交由人工裁决 | `needs_human` |
