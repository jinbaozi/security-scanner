# 组件档案扫描报告

## 基本信息

- **源码组件名称**: {component_name}
- **扫描时间**: {timestamp}
- **扫描文件数**: {source_count}
- **报告状态**: {report_status}

## 9 字段摘要

| 字段 | 值 | 来源类型 | 一致性 |
|------|----|---------|--------|
| 组件名称 | {field_component_name} | {field_component_name_src} | {field_component_name_status} |
| 版本号 | {field_version} | {field_version_src} | {field_version_status} |
| 供应商/作者 | {field_vendor} | {field_vendor_src} | {field_vendor_status} |
| 许可证 | {field_license} | {field_license_src} | {field_license_status} |
| 主语言/构建系统 | {field_language} | {field_language_src} | {field_language_status} |
| 入口/二进制 | {field_entry} | {field_entry_src} | {field_entry_status} |
| 运行时依赖 | {field_runtime_deps} | {field_runtime_deps_src} | {field_runtime_deps_status} |
| 构建依赖 | {field_build_deps} | {field_build_deps_src} | {field_build_deps_status} |
| 公开接口 | {field_public_api} | {field_public_api_src} | {field_public_api_status} |

## 声明 vs 实际 对账表

| 字段 | 声明值（manifest/SPEC/debian） | 实际值（源码/构建产物） | 偏差 | 严重度 |
|------|------------------------------|------------------------|------|--------|
| 组件名称 | {declared_name} | {actual_name} | {diff_name} | {sev_name} |
| 版本号 | {declared_version} | {actual_version} | {diff_version} | {sev_version} |
| 供应商/作者 | {declared_vendor} | {actual_vendor} | {diff_vendor} | {sev_vendor} |
| 许可证 | {declared_license} | {actual_license} | {diff_license} | {sev_license} |
| 主语言/构建系统 | {declared_language} | {actual_language} | {diff_language} | {sev_language} |
| 入口/二进制 | {declared_entry} | {actual_entry} | {diff_entry} | {sev_entry} |
| 运行时依赖 | {declared_runtime_deps} | {actual_runtime_deps} | {diff_runtime_deps} | {sev_runtime_deps} |
| 构建依赖 | {declared_build_deps} | {actual_build_deps} | {diff_build_deps} | {sev_build_deps} |
| 公开接口 | {declared_public_api} | {actual_public_api} | {diff_public_api} | {sev_public_api} |

## 详细 Findings

{component_findings_table}

## 红线违规汇总

| 红线 ID | 字段 | 严重度 | Finding 数量 | 涉及文件 |
|---------|------|--------|-------------|---------|
{red_line_summary_table}

## 问题汇总

- 严重问题: {critical_count} 项
- 高风险问题: {high_count} 项
- 中风险问题: {medium_count} 项
- 低风险问题: {low_count} 项
- 信息项: {info_count} 项
- 需人工确认: {needs_human_count} 项
- 未验证: {unverified_count} 项

## 修复建议

{component_suggestions}

## 未公开接口与敏感文件泄露

{comment_table}

{fileleak_table}

## 字段完整性要求

- 9 字段摘要表每行必须填写 4 个检查项（值、来源类型、一致性、备注列可附加），不允许空字段。
- 声明 vs 实际对账表每行必须填写 5 个检查项（声明值、实际值、偏差、严重度、证据列可附加）。
- 详细 finding 表每行包含 file、line、check_item、status、severity、verdict。
- 一致性列只能填写 `match` / `mismatch` / `unverified` / `不适用：{reason}`。

## 数据一致性要求

- 9 字段摘要中的字段数量必须与 spec section 4.2 的 9 项一致。
- 声明 vs 实际对账表的偏差必须与 JSON 中 `dimension=component-info` 的 findings 保持一致。
- 未公开接口表与敏感文件泄露表必须分别与 `dimension=comment` 和 `dimension=fileleak` 的 findings 保持一致。
- 使用 `references/personal-data-patterns.md` 知识库时，必须在质量审计结果中标注知识库最后更新时间。

## 质量审计结果

- 字段完整性审计: {field_integrity_audit}
- 数据一致性审计: {data_consistency_audit}
- 内容质量审计: {content_quality_audit}
- 覆盖完整性审计: {coverage_audit}
- 审计备注: {audit_notes}

## 降级输出说明

- **降级状态**: {degradation_status}
- **降级原因**: {degradation_reason}
- **缺失字段或未通过审计项**: {missing_or_failed_items}
- **后续处理建议**: {degradation_suggestion}
