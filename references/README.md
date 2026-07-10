# References 索引

本目录只存放跨 scanner / 跨阶段共享的 reference。维度专属 reference 放在 `scanners/<dim>/references/`，由该维 `meta.yaml` 引用。

## 顶层共享 References

| 文件 | 用途 | 加载时机 |
|------|------|----------|
| `allowlists.md` | 白名单与例外 | scanner session（`meta.references`） |
| `dependency-check.md` | Phase -1 环境预检 | Phase -1 |
| `library-vuln-caps.md` | 库版本知识库 | crypto/network session |
| `red-line-rules.md` | Pattern 权威源（**不**注入 scanner session） | 维护/生成维内 patterns |
| `finding-schema.md` | 统一 finding 字段 | Phase 1.5 / 2 / 3 |
| `redline-spec.md` | 40 条款原文 | Phase 3 A3b 仅 |
| `redline-mapping.md` | 条款↔RL↔维度映射 | Phase 3 A3b；切片生成输入 |
| `verdict-rules.md` | 裁决与去重权威 | Phase 2 |

## 维度专属 References

| Scanner | Reference |
|---------|-----------|
| `elf` | `checksec-guide.md` |
| `network` | `patterns-network.md` |
| `crypto` | `patterns-crypto.md` |
| `component-info` | `architecture-signals.md`, `personal-data-patterns.md` |
| 全部 13 维 | `redline-clauses.md`（由 `scripts/slice_redline_clauses.py` 生成） |

## redline 分层

权威链：`redline-spec.md` → `redline-mapping.md` → 维内 `redline-clauses.md` → 维内 `patterns-*.md`。

Scanner 不得直接加载顶层 `redline-spec.md` / `redline-mapping.md` / 整本 `red-line-rules.md`。
