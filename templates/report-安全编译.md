# 安全编译扫描报告

## 基本信息

- **源码组件名称**: {component_name}
- **扫描时间**: {timestamp}
- **扫描文件数**: {elf_count}
- **报告状态**: {report_status}

## 扫描结果

| 文件名 | 栈保护 | 堆栈不可执行 | GOT保护 | 地址无关代码 | 立即加载 | Strip | RPATH/RUNPATH | FORTIFY_SOURCE |
|--------|--------|-------------|---------|--------------|----------|-------|---------------|----------------|
{elf_results_table}

## 问题汇总

- 严重问题: {critical_count} 项
- 高风险问题: {high_count} 项
- 中风险问题: {medium_count} 项
- 低风险问题: {low_count} 项
- 信息项: {info_count} 项
- 需人工确认: {needs_human_count} 项
- 未验证: {unverified_count} 项

## 修复建议

{elf_suggestions}

## 字段完整性要求

- 结果表每行必须填写全部 8 个检查项，不允许空字段。
- 对不适用项填写“`不适用：{reason}`”，例如“`不适用：静态库无运行时装载项`”。
- `PASS` 项也应展示在表格中，用于形成完整安全编译矩阵。

## 数据一致性要求

- 表格中的文件数量必须等于基本信息中的扫描文件数。
- 问题汇总必须与 JSON 中 `dimension=elf` 的 findings 保持一致。
- 使用 `readelf` 降级扫描时，必须在质量审计结果中标记降级工具和缺失检查项。

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
