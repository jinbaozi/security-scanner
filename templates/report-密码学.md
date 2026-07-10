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
  - COMPONENT_VERSION
  - FILES_SCANNED
  - FAILED_AGENTS
  - RETRIED_AGENTS
  - DEGRADATION_NOTE
  - TIMESTAMP
---

# [[DISPLAY_NAME]] 详细报告

> 组件：[[COMPONENT_NAME]] | 扫描日期：[[SCAN_DATE]] | 维度：`[[DIM_KEY]]`
>
> 焦点：MD5/SHA1/弱随机数/TLS 配置

## 维度概览

| 项目 | 数量 |
|------|------|
| 失败 (FAIL) | [[FAIL_COUNT]] |
| 警告 (WARN) | [[WARN_COUNT]] |
| 通过 (PASS) | [[PASS_COUNT]] |
| **合计** | **[[TOTAL_COUNT]]** |

## 详细发现

[[SECTION_DETAIL]]

## 审计信息

[[SECTION_AUDIT]]

## 数据来源

- JSON 报告：`security-reports/security-scan-report-[[COMPONENT_NAME]]-[[SCAN_DATE]].json`
- 物化根：`security-reports/materialized/`
- 维度原始 finding：`security-reports/findings/findings-[[DIM_KEY]].json`

---
*本报告由 Security Compliance Scanner 自动生成于 [[TIMESTAMP]]*
