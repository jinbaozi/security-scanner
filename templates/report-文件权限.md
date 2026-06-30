# 文件权限扫描报告

## 基本信息

- **组件名称**: {component_name}
- **扫描时间**: {timestamp}
- **扫描文件数**: {scan_files}
- **扫描 Profile**: {scan_profile}
- **报告状态**: {report_status}
- **执行状态**: {execution_status}

## 扫描结果

| 文件路径 | 权限位 | 检查项 | 严重度 | 裁决 | 是否需要整改 | 说明 |
|----------|--------|--------|--------|------|--------------|------|
{permission_results_table}

## 按检查项分类统计

| 检查项 | 发现数 | 确认 | 疑似 | 需人工确认 | 未验证 |
|--------|--------|------|------|------------|--------|
| setuid_setgid | {setuid_setgid_count} | {setuid_setgid_confirmed} | {setuid_setgid_suspected} | {setuid_setgid_needs_human} | {setuid_setgid_unverified} |
| world_writable | {world_writable_count} | {world_writable_confirmed} | {world_writable_suspected} | {world_writable_needs_human} | {world_writable_unverified} |
| unexpected_executable | {unexpected_executable_count} | {unexpected_executable_confirmed} | {unexpected_executable_suspected} | {unexpected_executable_needs_human} | {unexpected_executable_unverified} |
| credential_file_permission | {credential_file_permission_count} | {credential_file_permission_confirmed} | {credential_file_permission_suspected} | {credential_file_permission_needs_human} | {credential_file_permission_unverified} |
| system_owned | {system_owned_count} | {system_owned_confirmed} | {system_owned_suspected} | {system_owned_needs_human} | {system_owned_unverified} |

## 问题汇总

- 严重问题: {critical_count} 项
- 高风险问题: {high_count} 项
- 中风险问题: {medium_count} 项
- 低风险问题: {low_count} 项
- 信息项: {info_count} 项
- 需人工确认: {needs_human_count} 项
- 未验证: {unverified_count} 项

## 修复建议

{permission_suggestions}

## 字段完整性要求

- 结果表每行必须包含文件路径、权限位、检查项、严重度、裁决、是否需要整改和说明。
- 对不适用项填写“`不适用：{reason}`”，不得使用空字段、`-`、`N/A` 或单独的“无”。
- “是否需要整改”只能填写“是”或“否”。
- “说明”必须不少于 10 个汉字，并说明权限位、文件类型和路径上下文。

## 数据一致性要求

- 结果表行数必须等于 JSON 中 `dimension=permission` 且 `verdict` 不为 `rejected` 的 findings 数量。
- 问题汇总必须与 JSON 中 `dimension=permission` 的裁决结果一致。
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
