# References 索引

本目录只存放跨 scanner 共享的 reference 文件。维度专属 reference 应放在对应的 `scanners/<dim>/references/` 目录中，并由该维度的 `meta.yaml` 使用相对路径引用。

## 顶层共享 References

以下文件允许保留在顶层 `references/`，用于多个 scanner 或跨阶段共享：

| 文件 | 用途 | 被哪些 scanner 引用 |
|------|------|---------------------|
| `allowlists.md` | 白名单与例外规则 | `comment`, `url`, `secret`, `fileleak`, `permission`, `elf`, `network`, `crypto`, `component-info` |
| `dependency-check.md` | Phase -1 环境预检与依赖检查 | 当前无 `scanners/*/meta.yaml` 直接引用 |
| `library-vuln-caps.md` | 库版本与不安全能力知识库 | `network`, `crypto` |
| `red-line-rules.md` | 跨维度红线规则库 | `network`, `crypto`, `component-info` |
| `verdict-rules.md` | Verdict Agent 裁决规则 | 当前无 `scanners/*/meta.yaml` 直接引用 |

## 维度专属 References

以下 reference 已下沉到各自 scanner 目录，不应再放在顶层 `references/`：

| Scanner | Reference |
|---------|-----------|
| `elf` | `scanners/elf/references/checksec-guide.md` |
| `network` | `scanners/network/references/patterns-network.md` |
| `crypto` | `scanners/crypto/references/patterns-crypto.md` |
| `component-info` | `scanners/component-info/references/architecture-signals.md` |
| `component-info` | `scanners/component-info/references/personal-data-patterns.md` |

新增 reference 时，先判断是否真正跨 scanner 共享；如果只服务单个维度，应放入该维度的 `scanners/<dim>/references/`。
