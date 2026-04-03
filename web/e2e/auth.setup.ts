import { test as setup } from '@playwright/test';

const authFile = 'playwright/.auth/user.json';

/**
 * 认证设置
 * 如果需要登录测试，取消注释并配置
 */
setup('authenticate', async ({ page }) => {
  // 示例：登录流程
  // await page.goto('/login');
  // await page.getByLabel('用户名').fill('user');
  // await page.getByLabel('密码').fill('password');
  // await page.getByRole('button', { name: '登录' }).click();
  
  // 等待登录完成
  // await page.waitForURL('/dashboard');
  
  // 保存状态
  // await page.context().storageState({ path: authFile });
});
