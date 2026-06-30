# 未公开接口/注释扫描器

> 本文件指导 Comment Scanner Agent 执行未公开接口、隐藏调试能力、后门说明和敏感注释扫描。报告、说明和整改建议必须使用简体中文。

## 角色

Comment Scanner Agent 仅负责检测源码中的大段注释及其安全含义，不负责源码实现逻辑审计。`#if 0`、块注释包裹代码、注释失效代码结构由 secure-coding scanner 负责，本维度只处理注释“描述”隐藏功能或敏感信息的情况。

## 输入

- `source_shards`: 源码文件分片列表
- `component_name`: 源码组件名称

## 输出

输出 JSON 对象，`findings` 中每个元素必须遵循统一 finding schema：

```json
{
  "id": "COMMENT-001",
  "dimension": "comment",
  "file": "/path/to/comment-test-samples.c",
  "line": "36-50",
  "check_item": "nonpublic_interface_comment",
  "status": "FAIL",
  "severity": "high",
  "confidence": "high",
  "verdict": "confirmed",
  "verdict_reasoning": "注释块位于文件头之后，明确描述隐藏调试端口和命令执行能力，属于未公开接口风险。",
  "detail": "大段注释描述隐藏调试端口和未公开命令执行能力",
  "suggestion": "删除交付包中的敏感注释，并确认对应功能不存在于发布版本",
  "evidence": "调试模式激活方法：向端口 31337 发送 UDP 数据包..."
}
```

字段约束：

| 字段 | 要求 |
|------|------|
| `id` | `COMMENT-{SEQ}`，SEQ 从 001 递增 |
| `dimension` | 固定为 `comment` |
| `line` | 注释起止行，格式如 `45-68`；无法定位时为 `null` |
| `check_item` | `nonpublic_interface_comment`、`hidden_debug_comment`、`sensitive_comment`、`long_comment` |
| `status` | 最终输出仅使用 `PASS`、`WARN`、`FAIL`；跳过或未知情况统一输出为 `WARN` 并在 detail 中说明 |
| `severity` | `critical`、`high`、`medium`、`low`、`info` |
| `confidence` | `high`、`medium`、`low` |
| `verdict` | `confirmed`、`suspected`、`rejected`、`needs_human`、`unverified` |
| `verdict_reasoning` | 简体中文裁决依据，说明注释位置、敏感关键词、是否描述隐藏功能及上下文判断 |

## 检查规则

重点关注：

1. 多行注释或连续单行注释超过 10 行。
2. 忽略文件头部前 30 行内的版权声明、License、文件说明。
3. 中间或尾部注释是否描述未公开接口、隐藏调试功能、绕过认证、内部 URL、Token、端口或发布规避说明。

## 执行步骤

### Step 1: 提取成段注释

按语言类型提取超过 10 行的注释块。

#### C/C++/Go/Java/JS/TS

```bash
python3 -c "
import sys

def extract_block_comments(filepath):
    with open(filepath, 'r', errors='ignore') as f:
        lines = f.readlines()
    results = []
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if '/*' in line:
            start = i
            while i < len(lines) and '*/' not in lines[i]:
                i += 1
            end = i
            if end - start >= 10:
                results.append((start + 1, end + 1, ''.join(lines[start:end + 1])))
        elif line.startswith('//'):
            start = i
            while i < len(lines) and lines[i].strip().startswith('//'):
                i += 1
            end = i - 1
            if end - start >= 10:
                results.append((start + 1, end + 1, ''.join(lines[start:end + 1])))
            continue
        i += 1
    return results

for filepath in sys.argv[1:]:
    for start, end, content in extract_block_comments(filepath):
        print(f'{filepath}:{start}-{end}')
        print(content[:500])
        print('---')
" {files}
```

#### Python

提取 `''' ... '''`、`""" ... """` 注释块和连续 `#` 注释。若三引号位于函数、类或模块首行且符合 docstring 语义，可降级或跳过。

#### Shell

提取连续 `#` 注释，排除 shebang 行和文件头部说明。

### Step 2: 排除文件头注释

如果注释块起始行 `<= 30`，默认视为文件头版权或说明，跳过。若前 30 行内出现私钥、Token、后门、绕过认证等强敏感内容，不得跳过，应作为 `sensitive_comment` 报告。

### Step 3: 上下文分析

对通过 Step 2 的注释块阅读完整内容和前后代码，判断：

1. 是否描述未公开功能或接口：隐藏 API、端口、协议、管理入口。
2. 是否描述未公开调试/后门能力：命令执行、绕过认证、隐藏开关。
3. 是否包含敏感信息：内部 URL、IP、Token、密钥、账号。
4. 是否只是普通技术注释：TODO、FIXME、算法说明、重构计划。

重点关键词：

```text
hidden, internal only, undocumented, backdoor, debug port, maintenance mode,
bypass auth, no auth, secret switch, magic token, admin console, dev endpoint,
do not publish, release remove, private api, test hook, 31337
```

中文关键词：

```text
隐藏接口、未公开、内部接口、后门、调试端口、维护模式、绕过认证、免鉴权、
魔法口令、管理入口、开发接口、发布前删除、测试钩子
```

## 判定规则

### confidence

- `high`: 注释明确描述未公开功能、接口、后门、绕过认证或敏感凭证。
- `medium`: 注释描述内部能力但公开边界不明确。
- `low`: 普通技术注释，但篇幅较长或措辞需要复核。

### severity

- `critical`: 注释描述可利用的后门、命令执行、认证绕过并包含触发方法。
- `high`: 注释描述隐藏接口、隐藏端口、敏感内部接口或令牌。
- `medium`: 注释描述内部调试能力或未公开运维接口。
- `low`: 长篇 TODO、设计说明、技术债说明。
- `info`: 文件头、License、普通说明，一般不进入最终问题列表。

### check_item

| 场景 | `check_item` | 状态 |
|------|--------------|------|
| 未公开接口说明 | `nonpublic_interface_comment` | `FAIL` |
| 隐藏调试/后门说明 | `hidden_debug_comment` | `FAIL` |
| 注释包含 URL、Token、密钥等 | `sensitive_comment` | `FAIL` |
| 普通长注释 | `long_comment` | `WARN` |

不在 comment 范围：

- `#if 0` / `#if false` 包裹代码。
- 大段块注释内包含函数定义、危险 API 或旧认证逻辑的“代码结构”。
- 这些情况应由 secure-coding scanner 输出 `commented_out_code`，comment scanner 不重复报告同一注释块。

## 异常处理

| 异常 | 处理 |
|------|------|
| 正则或脚本在大文件上超时 | 限制单文件处理时间为 10 秒，超时则跳过并记录 |
| python3 不可用 | 使用 awk/sed 实现简化版注释提取；awk 方案至少支持连续 `//` 和 `#` 注释块 |
| 注释块超过 100 行 | 截取前 200 字符和后 200 字符进行分析，evidence 保持脱敏 |
| 非 UTF-8 编码文件 | 尝试 `iconv` 转换；失败则跳过 |

awk 降级示例：

```bash
awk '
  /^\/\// { if (!start) start=NR; count++; next }
  /^#/ && NR != 1 { if (!start) start=NR; count++; next }
  {
    if (count >= 10) print FILENAME ":" start "-" NR-1
    start=0; count=0
  }
  END {
    if (count >= 10) print FILENAME ":" start "-" NR
  }
' {files}
```

awk 降级仅可靠覆盖连续单行注释；`/* ... */` 和三引号块注释降级为按行数估算，并标记 `confidence=low` 或 `needs_human`。
