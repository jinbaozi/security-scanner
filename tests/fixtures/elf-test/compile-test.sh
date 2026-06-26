#!/bin/bash
# 编译测试用 ELF 文件，用于验证 ELF Scanner 的检查逻辑。
# 需要 gcc 编译器；生成物仅用于本地测试，不应提交到交付包。

set -e

DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

cat > test_prog.c << 'EOF'
#include <stdio.h>
#include <string.h>

void vulnerable(char *input) {
    char buf[64];
    strcpy(buf, input);
    printf("%s\n", buf);
}

int main(int argc, char *argv[]) {
    if (argc > 1) vulnerable(argv[1]);
    return 0;
}
EOF

gcc -o test_full_secure test_prog.c \
  -fstack-protector-strong \
  -Wl,-z,relro,-z,now \
  -fPIE -pie \
  -Wl,-z,noexecstack \
  -D_FORTIFY_SOURCE=2 \
  -O2 2>/dev/null && echo "test_full_secure 编译成功" || echo "test_full_secure 编译失败"

gcc -o test_no_secure test_prog.c \
  -fno-stack-protector \
  -Wl,-z,norelro \
  -no-pie \
  -Wl,-z,execstack 2>/dev/null && echo "test_no_secure 编译成功" || echo "test_no_secure 编译失败"

gcc -o test_partial test_prog.c \
  -fstack-protector \
  -Wl,-z,relro \
  -fPIE -pie \
  -Wl,-z,noexecstack 2>/dev/null && echo "test_partial 编译成功" || echo "test_partial 编译失败"

cat > test_lib.c << 'EOF'
int add(int a, int b) { return a + b; }
EOF

gcc -shared -fPIC -o test_lib.so test_lib.c \
  -Wl,-z,relro,-z,now \
  -Wl,-z,noexecstack 2>/dev/null && echo "test_lib.so 编译成功" || echo "test_lib.so 编译失败"

cp test_full_secure test_stripped
strip test_stripped && echo "test_stripped strip 成功"

gcc -o test_rpath test_prog.c \
  -fstack-protector-strong \
  -Wl,-z,relro,-z,now \
  -fPIE -pie \
  -Wl,-z,noexecstack \
  -Wl,-rpath,/opt/custom/lib 2>/dev/null && echo "test_rpath 编译成功" || echo "test_rpath 编译失败"

gcc -o test_no_fortify test_prog.c \
  -fstack-protector-strong \
  -Wl,-z,relro,-z,now \
  -fPIE -pie \
  -Wl,-z,noexecstack \
  -U_FORTIFY_SOURCE 2>/dev/null && echo "test_no_fortify 编译成功" || echo "test_no_fortify 编译失败"

gcc -o test_not_stripped test_prog.c \
  -fstack-protector-strong \
  -Wl,-z,relro,-z,now \
  -fPIE -pie \
  -Wl,-z,noexecstack \
  -D_FORTIFY_SOURCE=2 \
  -O2 2>/dev/null && echo "test_not_stripped 编译成功" || echo "test_not_stripped 编译失败"

rm -f test_prog.c test_lib.c

echo "测试 ELF 文件生成完毕"
ls -la test_*
