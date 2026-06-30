# 完整性校验扫描报告

## 基本信息

- **组件名称**: {component_name}
- **扫描时间**: {timestamp}
- **扫描 Profile**: {scan_profile}
- **报告状态**: {report_status}

## 完整性总览

| 类别 | 状态 | 证据 | 备注 |
|------|------|------|------|
| 包签名 | {package_signature_status} | {package_signature_evidence} | RPM/DEB/cosign |
| 校验和 | {checksum_status} | {checksum_evidence} | sha256sum/gpg |
| 来源证明 | {provenance_status} | {provenance_evidence} | attestation/SLSA |
| 缺失项 | {integrity_missing_status} | {integrity_missing_evidence} | 需人工确认 |

## 详细 Findings

{integrity_findings_table}

## 修复建议

{integrity_suggestions}

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
