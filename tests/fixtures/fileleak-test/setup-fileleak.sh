#!/bin/bash
# 创建 FileLeak 测试用模拟文件。
# 生成物仅用于本地测试，不应提交到交付包。

set -e

DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

mkdir -p sample_project/src sample_project/config sample_project/certs sample_project/.ssh

echo 'DB_PASSWORD=super_secret_123' > sample_project/.env
echo 'API_KEY=sk-live-test-key-12345' > sample_project/.env.production

cat > sample_project/certs/server.pem <<'EOF'
-----BEGIN RSA PRIVATE KEY-----
MIIEowIBAAKCAQEA0Z3VS5JJcds3xfn/ygWyF8PbnGy0AHB7MhgHcTz6sE2I2yPB
aFEYhOBIcMOSKQNOGMQkFZPjFBbqsQpHnGkR2y0DmZPqWmHMzGKjUfSv+R3Y
-----END RSA PRIVATE KEY-----
EOF

cat > sample_project/certs/api.key <<'EOF'
-----BEGIN PRIVATE KEY-----
MIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQC7...
-----END PRIVATE KEY-----
EOF

cat > sample_project/.ssh/id_rsa <<'EOF'
-----BEGIN OPENSSH PRIVATE KEY-----
b3BlbnNzaC1rZXktdjEAAAAABG5vbmUAAAAEbm9uZQAAAAAAAAABAAAAMwAAAAtzc2gtZW
QyNTUxOQAAACBmN0VzN0h2Z0F1R1d0c3RyYWN0aW9uAAAA...
-----END OPENSSH PRIVATE KEY-----
EOF

echo '2024-01-15 ERROR: connection timeout' > sample_project/app.log
echo 'temporary build artifact' > sample_project/cache.tmp
echo 'backup of config' > sample_project/config.bak
touch sample_project/.DS_Store
touch sample_project/Thumbs.db
cat > sample_project/Makefile <<'EOF'
all:
	gcc -o app main.c
EOF
touch sample_project/certs/server.crt

echo 'package main' > sample_project/src/main.go
echo 'server:' > sample_project/config/app.yaml

echo "FileLeak 测试文件生成完毕"
ls -laR sample_project/
