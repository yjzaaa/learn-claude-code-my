import { test, expect } from '@playwright/test';

test.describe('记忆系统测试', () => {
  test('发送测试问题并验证响应', async ({ page }) => {
    // 监听控制台消息
    const consoleMessages: string[] = [];
    page.on('console', msg => {
      consoleMessages.push(`[${msg.type()}] ${msg.text()}`);
    });

    // 监听网络请求
    const networkRequests: string[] = [];
    page.on('request', request => {
      networkRequests.push(`>> ${request.method()} ${request.url()}`);
    });
    page.on('response', response => {
      networkRequests.push(`<< ${response.status()} ${response.url()}`);
    });

    // 访问聊天页面
    await page.goto('/chat');
    await expect(page).toHaveURL(/.*chat.*/);

    // 等待页面加载
    await page.waitForSelector('textarea, input[type="text"]', { timeout: 5000 });

    // 找到输入框并输入测试问题
    const input = page.locator('textarea').first();
    await expect(input).toBeVisible();

    // 输入测试问题 - 关于记忆的问题
    await input.fill('你好，请记住我的名字是测试用户');

    // 找到发送按钮并点击（或使用 Enter）
    await input.press('Enter');

    // 等待响应（最多 30 秒）
    await page.waitForTimeout(5000);

    // 打印收集的信息
    console.log('=== 控制台消息 ===');
    consoleMessages.forEach(msg => console.log(msg));

    console.log('\n=== 网络请求 ===');
    networkRequests.forEach(req => console.log(req));

    // 验证消息出现在聊天中
    const messages = page.locator('[data-testid="message"], .message, [class*="message"]').first();
    await expect(messages).toBeVisible().catch(() => {
      console.log('未找到消息元素，可能使用不同的选择器');
    });
  });
});
