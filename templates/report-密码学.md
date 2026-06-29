# 密码学合规扫描报告

## 基本信息

- **源码组件名称**: {component_name}
- **扫描时间**: {timestamp}
- **扫描文件数**: {source_count}
- **报告状态**: {report_status}

## 算法使用总览

| 类别 | 使用的算法 | 红线违规 | 备注 |
|------|----------|---------|------|
| 对称算法 | {symmetric_list} | {symmetric_red_line} | - |
| 非对称算法 | {asymmetric_list} | {asymmetric_red_line} | - |
| Hash 算法 | {hash_list} | {hash_red_line} | - |
| 自定义算法 | {custom_list} | {custom_red_line} | - |
| 伪加密 | {pseudo_list} | {pseudo_red_line} | - |
| 随机数 API | {random_list} | {random_red_line} | - |

## 详细 Findings

{crypto_findings_table}

## 红线违规汇总

| 红线 ID | 类别 | 严重度 | Finding 数量 | 涉及文件 |
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

{crypto_suggestions}

## 库版本与不安全能力

{library_vuln_table}

## 字段完整性要求

- 算法总览表每行必须填写全部 6 个检查项。
- 对不适用项填写"不适用：{reason}"。
- 详细 finding 表每行包含 file、line、check_item、status、severity、verdict。

## 数据一致性要求

- 算法总览中的算法数量必须等于 findings 中对应类别的去重数量。
- 红线违规汇总必须与 JSON 中 `dimension=crypto` 的 findings 保持一致。
- 使用 `references/library-vuln-caps.md` 知识库时，必须在质量审计结果中标注知识库最后更新时间。

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
