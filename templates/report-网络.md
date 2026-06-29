# 网络合规扫描报告

## 基本信息

- **源码组件名称**: {component_name}
- **扫描时间**: {timestamp}
- **扫描文件数**: {source_count}
- **报告状态**: {report_status}

## 网络协议与端口总览

| 协议 | 端口/服务 | 加密状态 | 红线违规 | 备注 |
|------|----------|---------|---------|------|
| {protocol_list} | {port_list} | {tls_status} | {protocol_red_line} | - |

## 详细 Findings

{network_findings_table}

## 红线违规汇总

| 红线 ID | 协议/服务 | 严重度 | Finding 数量 | 涉及文件 |
|---------|----------|--------|-------------|---------|
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

{network_suggestions}

## 公网地址与外部依赖

{public_address_table}

## 字段完整性要求

- 网络协议与端口总览表每行必须填写全部 5 个检查项。
- 对不适用项填写"不适用：{reason}"。
- 详细 finding 表每行包含 file、line、check_item、status、severity、verdict。
- 公网地址与外部依赖表每行包含 address、port、protocol、verdict。

## 数据一致性要求

- 协议总览中的协议数量必须等于 findings 中对应类别的去重数量。
- 红线违规汇总必须与 JSON 中 `dimension=network` 的 findings 保持一致。
- 使用 `references/network-redline.md` 知识库时，必须在质量审计结果中标注知识库最后更新时间。

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
