# 公网地址扫描报告

## 基本信息

- **源码组件名称**: {component_name}
- **扫描时间**: {timestamp}
- **扫描文件数**: {file_count}
- **报告状态**: {report_status}

## 扫描结果

| 源码组件名称 | 发现地址（IP/URL/邮箱） | 位置（文件/脚本/路径） | 是否需要整改 | 说明 |
|--------------|--------------------------|-------------------------|--------------|------|
{url_results_table}

## 问题汇总

- 需要整改: {need_fix_count} 项
- 无需整改（例外场景）: {no_fix_count} 项
- 疑似问题: {suspected_count} 项
- 需人工确认: {needs_human_count} 项
- 未验证: {unverified_count} 项

## 字段完整性要求

- “发现地址”必须保留可定位的 IP、URL、域名或邮箱；敏感值如需脱敏，必须保留可比对前后缀。
- “位置”必须包含文件路径和行号；无行号时填写“`不适用：scanner 未提供行号，见 evidence`”。
- “是否需要整改”只能填写“是”或“否”，不得填写“待定”。
- “说明”必须不少于 10 个汉字，并明确说明确认、疑似、例外或降级原因。

## 数据一致性要求

- “需要整改”数量必须等于 `confirmed` 且非例外场景的公网地址 findings 数量。
- “无需整改”数量必须等于已裁决为例外场景或 `rejected` 的记录数量，并进入审计日志。
- 所有 `confirmed` 和 `suspected` 的 URL findings 必须出现在本报告表格中。

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
