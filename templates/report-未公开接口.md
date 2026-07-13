---
required:
  - COMPONENT_NAME
  - SCAN_DATE
  - DIM_KEY
  - DISPLAY_NAME
  - FAIL_COUNT
  - WARN_COUNT
  - PASS_COUNT
  - TOTAL_COUNT
  - SECTION_DETAIL
  - SECTION_AUDIT
optional:
  - DEGRADATION_NOTE
  - TIMESTAMP
---

# [[DISPLAY_NAME]] 详细报告

> 组件：[[COMPONENT_NAME]] | 扫描日期：[[SCAN_DATE]] | 维度：`[[DIM_KEY]]`
>
> 焦点：注释中描述的隐藏接口/调试入口/TODO

## 问题汇总

| 项目 | 数量 |
|------|------|
| 失败 (FAIL) | [[FAIL_COUNT]] |
| 警告 (WARN) | [[WARN_COUNT]] |
| 通过 (PASS) | [[PASS_COUNT]] |
| **合计** | **[[TOTAL_COUNT]]** |

## 详细发现

[[SECTION_DETAIL]]

## 质量审计结果

[[SECTION_AUDIT]]

## 降级输出说明

[[DEGRADATION_NOTE]]

## 数据来源

- JSON 报告：`security-reports/security-scan-report-[[COMPONENT_NAME]]-[[SCAN_DATE]].json`
- 物化根：`security-reports/materialized/`
- 维度原始 finding：`security-reports/findings/findings-[[DIM_KEY]].json`

---
*本报告由 Security Compliance Scanner 自动生成于 [[TIMESTAMP]]*
