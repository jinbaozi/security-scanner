# 口令和硬编码扫描报告

## 基本信息

- **源码组件名称**: {component_name}
- **扫描时间**: {timestamp}
- **扫描文件数**: {file_count}
- **报告状态**: {report_status}

## 扫描结果

| 源码组件名称 | 发现内容 | 位置（文件/脚本/路径） | 说明 |
|--------------|----------|-------------------------|------|
{secret_results_table}

## 问题汇总

- 确认硬编码凭证: {confirmed_count} 项
- 疑似硬编码: {suspected_count} 项
- 低置信度（仅变量名匹配）: {low_count} 项
- 需人工确认: {needs_human_count} 项
- 未验证: {unverified_count} 项

## 字段完整性要求

- “发现内容”必须做最小必要脱敏，例如保留类型、键名和可比对前后缀，不得完整暴露真实密钥。
- “位置”必须包含文件路径和行号；无行号时填写“`不适用：scanner 未提供行号，见 evidence`”。
- “说明”必须不少于 10 个汉字，并说明为何判定为确认、疑似、低置信度或例外。
- 空字符串、环境变量引用和占位符不得作为确认硬编码凭证。

## 数据一致性要求

- `confirmed`、`suspected`、`needs_human` 和 `unverified` 的 secret findings 必须出现在本报告或降级说明中。
- `rejected` secret findings 不计入问题汇总，但必须进入审计日志。
- 问题汇总数量必须与 JSON 中 `dimension=secret` 的裁决结果一致。

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
