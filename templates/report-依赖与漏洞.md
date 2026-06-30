# 依赖与漏洞扫描报告

## 基本信息

- **组件名称**: {component_name}
- **扫描时间**: {timestamp}
- **扫描 Profile**: {scan_profile}
- **报告状态**: {report_status}

## SBOM 总览

| 指标 | 数量 | 备注 |
|------|------|------|
| 依赖总数 | {dependency_total} | 来自 lock/manifest/SBOM |
| 缺失 lock 文件 | {missing_lock_count} | 不计入其他维度重复 WARN |
| 已知漏洞依赖 | {vulnerable_dependency_count} | CVSS >= 7 为 FAIL |
| EOM/EOL 组件 | {outdated_component_count} | 需人工确认生命周期 |

## 详细 Findings

{dependency_findings_table}

## SBOM 明细

{sbom_table}

## 修复建议

{dependency_suggestions}

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
