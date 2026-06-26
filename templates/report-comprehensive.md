# 安全合规扫描综合报告

## 基本信息

- **扫描目标**: {target_path}
- **组件名称**: {component_name}
- **扫描时间**: {timestamp}
- **扫描工具版本**: Security Compliance Scanner v1.0
- **扫描耗时**: {duration} 秒
- **报告状态**: {report_status}

## 扫描统计

- **总文件数**: {total_files}
- **扫描文件数**: {scan_files}
- **排除文件数**: {excluded_files}（第三方、生成代码或扫描策略排除）
- **ELF 文件数**: {elf_count}
- **源码文件数**: {source_count}
- **配置文件数**: {config_count}

## 发现汇总

| 严重度 | 数量 |
|--------|------|
| 严重（Critical） | {critical_count} |
| 高（High） | {high_count} |
| 中（Medium） | {medium_count} |
| 低（Low） | {low_count} |
| 信息（Info） | {info_count} |
| **总计** | **{total_findings}** |

## 各维度发现统计

| 维度 | 发现数 | 确认 | 疑似 | 需人工确认 | 未验证 | 排除 |
|------|--------|------|------|------------|--------|------|
| ELF 安全编译 | {elf_total} | {elf_confirmed} | {elf_suspected} | {elf_needs_human} | {elf_unverified} | {elf_rejected} |
| 公网地址 | {url_total} | {url_confirmed} | {url_suspected} | {url_needs_human} | {url_unverified} | {url_rejected} |
| 口令和硬编码 | {secret_total} | {secret_confirmed} | {secret_suspected} | {secret_needs_human} | {secret_unverified} | {secret_rejected} |
| 未公开接口 | {comment_total} | {comment_confirmed} | {comment_suspected} | {comment_needs_human} | {comment_unverified} | {comment_rejected} |
| 敏感文件泄露 | {fileleak_total} | {fileleak_confirmed} | {fileleak_suspected} | {fileleak_needs_human} | {fileleak_unverified} | {fileleak_rejected} |
| 文件权限 | {perm_total} | {perm_confirmed} | {perm_suspected} | {perm_needs_human} | {perm_unverified} | {perm_rejected} |

## 详细发现

### ELF 安全编译

{elf_findings_detail}

### 公网地址

{url_findings_detail}

### 口令和硬编码

{secret_findings_detail}

### 未公开接口

{comment_findings_detail}

### 敏感文件泄露

{fileleak_findings_detail}

### 文件权限

{perm_findings_detail}

## 字段完整性说明

- 所有 finding 记录必须包含 `id`、`dimension`、`file`、`line`、`check_item`、`status`、`severity`、`confidence`、`verdict`、`detail`、`suggestion`、`evidence`。
- 无行号或不适用字段必须填写“`不适用：{reason}`”，不得使用空值、`-`、`N/A` 或单独的“无”作为占位符。
- 所有 `confirmed`、`suspected`、`needs_human`、`unverified` 记录必须在本报告或审计日志中可追溯到原始 evidence。

## 数据一致性说明

- 严重度汇总数量必须等于 JSON `summary.by_severity`。
- 各维度发现统计必须等于 JSON `summary.by_dimension` 与 `summary.by_verdict` 的组合结果。
- 专项报告中的问题数量必须与本综合报告的对应维度数量一致。
- `rejected` finding 只进入审计日志，不计入正式问题总数。

## 审计日志

- Recon 覆盖率: {recon_coverage}
- 失败的 Agent: {failed_agents}
- 重试的 Agent: {retried_agents}
- 降级的维度: {degraded_dimensions}
- 被排除的 findings: {rejected_findings}
- 需人工确认的 findings: {needs_human_findings}
- 未验证的 findings: {unverified_findings}

## 质量审计结果

- 字段完整性审计: {field_integrity_audit}
- 数据一致性审计: {data_consistency_audit}
- 内容质量审计: {content_quality_audit}
- 覆盖完整性审计: {coverage_audit}
- 审计备注: {audit_notes}

## 降级输出说明

当 findings 数据不完整、JSON schema 校验失败、Markdown 渲染失败或输出文件写入失败时，本报告必须保留已完成结果，并在本节标记降级原因：

- **降级状态**: {degradation_status}
- **降级原因**: {degradation_reason}
- **受影响维度**: {degraded_dimensions}
- **缺失字段或未通过审计项**: {missing_or_failed_items}
- **后续处理建议**: {degradation_suggestion}

## 免责声明

本报告由 AI 辅助生成，可能存在误报或遗漏。建议对 critical 和 high severity 的发现进行人工复核；对 `needs_human` 和 `unverified` 项必须由人工确认后再作为最终整改依据。
