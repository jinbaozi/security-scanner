#!/bin/bash
# 端到端测试用权限设置脚本

DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$DIR"

chmod 666 config/app.yaml 2>/dev/null || true
chmod 755 src/main.go 2>/dev/null || true
