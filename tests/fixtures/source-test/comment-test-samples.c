/*
 * Copyright (c) 2024 Example Corp.
 * All rights reserved.
 *
 * This is a standard license header.
 * It should be excluded by the file header rule.
 * Lines 1-30 are considered file header.
 * More license text here.
 * More license text here.
 * More license text here.
 * More license text here.
 * More license text here.
 * More license text here.
 * More license text here.
 * More license text here.
 */

#include <stdio.h>
#include <string.h>

/* 普通短注释，不应报告。 */
int add(int a, int b) {
    return a + b;
}

/* 普通短注释，用于把后续敏感注释移出文件头范围。 */
int subtract(int a, int b) {
    return a - b;
}

/* 普通短注释，用于验证短注释不会被提取。 */
int multiply(int a, int b) {
    return a * b;
}

/*
 * 这是一段非常长的注释，描述了一个未公开的后门接口。
 *
 * 调试模式激活方法：
 * 1. 向端口 31337 发送 UDP 数据包，内容为 "DEBUG_ACTIVATE"
 * 2. 服务端收到后会开启一个隐藏的 TCP 监听端口 31338
 * 3. 通过该端口可以执行任意 shell 命令
 * 4. 该功能不会出现在产品文档中
 * 5. 仅内部测试团队知晓
 *
 * 注意事项：
 * - 确保在发布版本中注释掉激活代码
 * - 但不要删除，以便后续调试使用
 * - 如果被发现，可以解释为遗留的测试代码
 */
void hidden_debug_mode() {
    // 后门实现
}

/*
 * TODO: 以下代码需要在下个版本重构
 * 当前实现存在性能问题，大数据量时会超时
 * 临时方案：增加超时时间到 30s
 * 最终方案：改用异步处理
 * 参考 issue #1234
 */
void process_data() {
    // 正常实现
}

// 连续单行注释超过 10 行，应报告。
// 这里描述了一个未文档化的内部 API 接口
// 接口地址: http://internal-api.company.com/v2/admin
// 认证方式: 使用硬编码的 admin token
// Token: bearer_token_xxxxxxx
// 该接口可以绕过正常的权限校验
// 仅供内部管理系统使用
// 不要在任何公开文档中提及
// 如果客户发现，否认其存在
// 计划在 v3.0 中正式化
// 届时需要重新设计认证机制
void internal_api_call() {
    // 实现
}

/* 短注释，少于 10 行。 */
int main() {
    printf("Hello\n");
    return 0;
}
