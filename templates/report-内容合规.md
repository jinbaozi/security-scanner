# 内容合规扫描报告

## 基本信息

- **组件名称**: {component_name}
- **扫描时间**: {timestamp}
- **扫描 Profile**: {scan_profile}
- **报告状态**: {report_status}

## 内容合规总览

| 类别 | Finding 数量 | 默认裁决 | 备注 |
|------|--------------|----------|------|
| 政治敏感表述 | {political_sensitive_term_count} | needs_human | 需人工合规审核 |
| 地理名称错称 | {forbidden_geography_name_count} | needs_human | 需人工合规审核 |
| 地图资源 | {map_resource_presence_count} | needs_human | 需版图完整性审核 |
| 审核记录缺失 | {content_review_missing_count} | needs_human | 需流程补充 |

## 详细 Findings

{content_compliance_findings_table}

## 人工复核清单

{content_compliance_manual_review_table}

## 修复建议

{content_compliance_suggestions}

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
