#!/bin/bash
# 创建 Permission 测试用文件并设置权限。
# 需要 root 权限来设置 setuid/setgid；无 root 时跳过 setuid 测试。
# 生成物仅用于本地测试。

set -e

DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

mkdir -p sample_perms

cp /bin/ls sample_perms/suid_binary 2>/dev/null || echo "SKIP: 无权限复制 /bin/ls，跳过 setuid 测试"
chmod u+s sample_perms/suid_binary 2>/dev/null || true

cp /bin/ls sample_perms/sgid_binary 2>/dev/null || echo "SKIP: 无权限复制 /bin/ls，跳过 setgid 测试"
chmod g+s sample_perms/sgid_binary 2>/dev/null || true

echo "world writable config" > sample_perms/world_writable.conf
chmod 666 sample_perms/world_writable.conf

cat > sample_perms/unexpected_exec.py <<'EOF'
#!/usr/bin/env python3
print("hello")
EOF
chmod 755 sample_perms/unexpected_exec.py

cat > sample_perms/install.sh <<'EOF'
#!/bin/bash
echo "installing..."
EOF
chmod 755 sample_perms/install.sh

echo 'normal file' > sample_perms/normal.txt
chmod 644 sample_perms/normal.txt

echo "Permission 测试文件生成完毕"
ls -la sample_perms/
