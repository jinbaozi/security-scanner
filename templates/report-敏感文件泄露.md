# 敏感文件泄露扫描报告

## 基本信息

- **组件名称**: {component_name}
- **扫描时间**: {timestamp}
- **扫描文件数**: {scan_files}
- **扫描 Profile**: {scan_profile}
- **报告状态**: {report_status}
- **执行状态**: {execution_status}

## 扫描结果

| 文件路径 | 检查项 | 严重度 | 裁决 | 是否需要整改 | 说明 |
|----------|--------|--------|------|--------------|------|
{fileleak_results_table}

## 按检查项分类统计

| 检查项 | 发现数 | 确认 | 疑似 | 需人工确认 | 未验证 |
|--------|--------|------|------|------------|--------|
| env_file | {env_file_count} | {env_file_confirmed} | {env_file_suspected} | {env_file_needs_human} | {env_file_unverified} |
| private_key_file | {private_key_file_count} | {private_key_file_confirmed} | {private_key_file_suspected} | {private_key_file_needs_human} | {private_key_file_unverified} |
| ssh_private_key_file | {ssh_private_key_file_count} | {ssh_private_key_file_confirmed} | {ssh_private_key_file_suspected} | {ssh_private_key_file_needs_human} | {ssh_private_key_file_unverified} |
| authorized_keys | {authorized_keys_count} | {authorized_keys_confirmed} | {authorized_keys_suspected} | {authorized_keys_needs_human} | {authorized_keys_unverified} |
| dev_tool_binary | {dev_tool_binary_count} | {dev_tool_binary_confirmed} | {dev_tool_binary_suspected} | {dev_tool_binary_needs_human} | {dev_tool_binary_unverified} |
| password_crack_tool | {password_crack_tool_count} | {password_crack_tool_confirmed} | {password_crack_tool_suspected} | {password_crack_tool_needs_human} | {password_crack_tool_unverified} |
| temp_or_log_file | {temp_or_log_file_count} | {temp_or_log_file_confirmed} | {temp_or_log_file_suspected} | {temp_or_log_file_needs_human} | {temp_or_log_file_unverified} |
| core_dump | {core_dump_count} | {core_dump_confirmed} | {core_dump_suspected} | {core_dump_needs_human} | {core_dump_unverified} |
| build_file | {build_file_count} | {build_file_confirmed} | {build_file_suspected} | {build_file_needs_human} | {build_file_unverified} |
| os_generated_file | {os_generated_file_count} | {os_generated_file_confirmed} | {os_generated_file_suspected} | {os_generated_file_needs_human} | {os_generated_file_unverified} |
| certificate_file | {certificate_file_count} | {certificate_file_confirmed} | {certificate_file_suspected} | {certificate_file_needs_human} | {certificate_file_unverified} |
| malware_scan | {malware_scan_count} | {malware_scan_confirmed} | {malware_scan_suspected} | {malware_scan_needs_human} | {malware_scan_unverified} |

## 问题汇总

- 严重问题: {critical_count} 项
- 高风险问题: {high_count} 项
- 中风险问题: {medium_count} 项
- 低风险问题: {low_count} 项
- 信息项: {info_count} 项
- 需人工确认: {needs_human_count} 项
- 未验证: {unverified_count} 项

## 修复建议

{fileleak_suggestions}

## 字段完整性要求

- 结果表每行必须包含文件路径、检查项、严重度、裁决、是否需要整改和说明。
- 对不适用项填写“`不适用：{reason}`”，不得使用空字段、`-`、`N/A` 或单独的“无”。
- “是否需要整改”只能填写“是”或“否”。
- “说明”必须不少于 10 个汉字，并说明文件名模式、内容确认结果或降级原因。

## 数据一致性要求

- 结果表行数必须等于 JSON 中 `dimension=fileleak` 且 `verdict` 不为 `rejected` 的 findings 数量。
- 问题汇总必须与 JSON 中 `dimension=fileleak` 的裁决结果一致。
- `rejected` finding 不计入问题汇总，但必须进入审计日志。

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
