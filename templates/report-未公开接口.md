# 未公开接口扫描报告

## 基本信息

- **源码组件名称**: {component_name}
- **扫描时间**: {timestamp}
- **扫描文件数**: {file_count}
- **报告状态**: {report_status}

## 扫描结果

| 源码组件名称 | 脚本路径 | 解释性语言类型 | 成段注释起止行 | 涉及功能描述 | 是否为未公开接口 | 说明 |
|--------------|----------|----------------|----------------|--------------|------------------|------|
{comment_results_table}

## 问题汇总

- 确认未公开接口: {confirmed_count} 项
- 疑似未公开接口: {suspected_count} 项
- 普通长注释: {low_count} 项
- 需人工确认: {needs_human_count} 项
- 未验证: {unverified_count} 项

## 字段完整性要求

- “脚本路径”必须包含可定位文件路径。
- “解释性语言类型”必须填写实际语言或“`不适用：非解释性语言但包含成段注释`”。
- “成段注释起止行”必须填写起止行范围；无法定位时填写“`不适用：scanner 未提供行号，见 evidence`”。
- “是否为未公开接口”只能填写“是”或“否”，无法判断时应进入“需人工确认”并在说明中写明原因。
- “说明”必须不少于 10 个汉字，并引用注释中触发判断的功能描述。

## 数据一致性要求

- 所有 `confirmed` 和 `suspected` 的 comment findings 必须出现在本报告。
- 普通 TODO、算法说明和开发备注若被排除，必须进入审计日志，不得计入确认未公开接口。
- 问题汇总数量必须与 JSON 中 `dimension=comment` 的裁决结果一致。

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
