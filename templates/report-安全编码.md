# 安全编码扫描报告

## 基本信息

- **组件名称**: {component_name}
- **扫描时间**: {timestamp}
- **扫描 Profile**: {scan_profile}
- **报告状态**: {report_status}

## 安全编码总览

| 类别 | Finding 数量 | 需人工确认 | 备注 |
|------|--------------|------------|------|
| 危险函数 | {unsafe_function_count} | {unsafe_function_needs_human} | C/C++ 与命令执行 API |
| 安全函数失效 | {safe_function_disabled_count} | {safe_function_disabled_needs_human} | 宏降级和错误封装 |
| 注释失效代码 | {commented_out_code_count} | {commented_out_code_needs_human} | 与 comment scanner 去重 |
| SAST 结果 | {sast_finding_count} | {sast_finding_needs_human} | 可选工具输入 |

## 详细 Findings

{secure_coding_findings_table}

## 修复建议

{secure_coding_suggestions}

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
