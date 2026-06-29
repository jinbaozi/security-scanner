from django.db import models
import telnetlib

class User(models.Model):
    name = models.CharField(max_length=100)        # PII: 姓名
    phone = models.CharField(max_length=20)       # PII: 手机号 (RL-141: 明文)
    id_card = models.CharField(max_length=18)      # PII: 身份证 (RL-140: 明文)

ADMIN_USER = "admin"        # RL-160: 默认账号
ADMIN_PASS = "admin123"     # RL-160: 默认密码