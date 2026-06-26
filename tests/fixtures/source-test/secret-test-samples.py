import os

# 硬编码密码，应报告。
DB_PASSWORD = "SuperSecret123!"
ADMIN_PWD = "admin@2024"

# API 密钥硬编码，应报告。
API_KEY = "sk-live-abc123def456ghi789"
AWS_ACCESS_KEY = "AKIAIOSFODNN7EXAMPLE"

# 环境变量引用，不应报告。
safe_password = os.environ.get("DB_PASSWORD")
safe_key = os.getenv("API_KEY", "")


# 函数参数名，不应报告。
def authenticate(username, password):
    """验证用户凭证。"""
    return check_credentials(username, password)


# 加密函数定义，不应报告。
def encrypt(data, key):
    return aes_encrypt(data, key)


def decrypt(data, key):
    return aes_decrypt(data, key)


# SSH 私钥头，应报告。
SSH_KEY = """-----BEGIN RSA PRIVATE KEY-----
MIIEowIBAAKCAQEA...
-----END RSA PRIVATE KEY-----"""

# 疑似 Base64 编码凭证，应报告。
ENCODED_SECRET = "cGFzc3dvcmQxMjM0NTY3ODkwYWJjZGVm"

# 占位符，不应报告。
TEMPLATE_PASSWORD = "${DB_PASSWORD}"
PLACEHOLDER_KEY = "YOUR_API_KEY_HERE"
