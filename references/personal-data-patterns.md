# 个人数据 Patterns 库

> 本文件集中维护个人数据字段名和违规处理 pattern。component-info-scanner 引用此文件。

## 1. 个人数据字段名 Pattern

### 1.1 类别与 Pattern

| 类别 | Pattern | 严重度（明文存储/HTTP 传输） |
|------|---------|----------------------------|
| 姓名 | `\b(?:name|username|real_name|full_name|user_name)\b` | medium |
| 手机号 | `\b(?:phone|mobile|tel|cellphone|phone_number|mobile_number)\b` | high |
| 身份证 | `\b(?:id_card|idcard|identity|id_number|identity_card|citizen_id)\b` | critical |
| 邮箱 | `\b(?:email|mail|e_mail|email_address)\b` | medium |
| 位置 | `\b(?:location|gps|latitude|longitude|address|geo)\b` | high |
| 设备标识 | `\b(?:device_id|imei|mac|udid|android_id|idfa|gaid)\b` | high |
| 银行卡 | `\b(?:bank_card|card_number|credit_card|cc_number)\b` | critical |
| 出生日期 | `\b(?:birthday|birth_date|dob)\b` | medium |
| 头像 | `\b(?:avatar|profile_photo|head_image)\b` | low |
| IP 地址 | `\b(?:ip|ip_address|client_ip|remote_ip)\b` | low |

### 1.2 跨语言字段命名变体

| 类别 | snake_case | camelCase | PascalCase |
|------|-----------|-----------|------------|
| 姓名 | `user_name` | `userName` | `UserName` |
| 手机号 | `phone_number` | `phoneNumber` | `PhoneNumber` |
| 身份证 | `id_card` | `idCard` | `IdCard` |
| 邮箱 | `email` | `email` | `Email` |

Pattern 须同时支持三种命名约定（用 `\b` + 字符集 `[a-zA-Z_0-9]` 包围）。

## 2. 违规处理 Pattern

### 2.1 明文存储（红线 RL-140 ~ RL-142）

```regex
(?:id_card|idcard|phone|mobile|email|bank_card|identity).{0,80}(?:=|:)\s*["'][^"']{4,}["']
```

排除：上下文包含 `encrypt|hash|mask|hmac|bcrypt|cipher|secrets\.|SystemRandom` 时不告警。

### 2.2 HTTP 明文传输（红线 RL-143）

```regex
http://[^"'\s]*(?:id_card|phone|idcard|mobile|email|bank_card|identity_card)
```

### 2.3 日志明文（红线 RL-144）

```regex
logger\.(?:info|debug|error|warn|fatal)\s*\([^)]*(?:email|mail|phone|mobile|id_card|idcard)\b
```

排除：上下文包含 `mask|redact|truncate|hash|md5|sha` 时不告警。

## 3. 用途分类

| 字段 | 常见用途 | 风险 |
|------|---------|------|
| 姓名 | 用户标识、订单、收件人 | medium |
| 手机号 | 短信验证、紧急联系、收件人 | high（易被滥用做骚扰） |
| 身份证 | 实名认证、年龄校验 | critical（一旦泄露难注销） |
| 邮箱 | 通知、找回密码 | medium |
| 位置 | 导航、签到、附近的人 | high（可定位家庭住址） |
| 设备标识 | 推送、用户追踪、广告 | high（用户画像） |
| 银行卡 | 支付 | critical（资金风险） |

## 4. 用户自定义字段

在下方添加项目特定的个人数据字段：

<!-- 示例:
| 类别 | 字段 | severity |
| 医疗 | medical_record | critical |
-->
