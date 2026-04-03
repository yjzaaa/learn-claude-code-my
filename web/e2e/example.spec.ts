import { test, expect } from '@playwright/test';

test.describe('首页测试', () => {
  test('页面标题正确', async ({ page }) => {
    await page.goto('/');
    await expect(page).toHaveTitle(/Claude Code|Learn/);
  });

  test('导航栏可见', async ({ page }) => {
    await page.goto('/');
    const nav = page.locator('nav, header').first();
    await expect(nav).toBeVisible();
  });

  test('响应式布局', async ({ page }) => {
    await page.goto('/');
    
    // 桌面尺寸
    await page.setViewportSize({ width: 1280, height: 720 });
    await expect(page.locator('body')).toBeVisible();
    
    // 移动端尺寸
    await page.setViewportSize({ width: 375, height: 667 });
    await expect(page.locator('body')).toBeVisible();
  });
});

test.describe('聊天功能', () => {
  test('聊天页面可访问', async ({ page }) => {
    await page.goto('/chat');
    await expect(page).toHaveURL(/.*chat.*/);
  });

  test('输入框存在', async ({ page }) => {
    await page.goto('/chat');
    const input = page.locator('textarea, input[type="text"]').first();
    await expect(input).toBeVisible();
  });
});
