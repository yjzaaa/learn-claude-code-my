import { defineConfig, devices } from '@playwright/test';

/**
 * Playwright 配置文件
 * @see https://playwright.dev/docs/test-configuration
 */
export default defineConfig({
  testDir: './e2e',
  
  /* 并发运行测试 */
  fullyParallel: true,
  
  /* 失败时禁止并行 */
  forbidOnly: !!process.env.CI,
  
  /* 失败重试次数 */
  retries: process.env.CI ? 2 : 0,
  
  /* 并行工作数 */
  workers: process.env.CI ? 1 : undefined,
  
  /* 报告器 */
  reporter: 'html',
  
  /* 共享配置 */
  use: {
    /* 基础 URL */
    baseURL: 'http://localhost:3000',
    
    /* 收集追踪信息 */
    trace: 'on-first-retry',
    
    /* 截图 */
    screenshot: 'only-on-failure',
    
    /* 视频录制 */
    video: 'on-first-retry',
  },

  /* 项目配置 */
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
    {
      name: 'firefox',
      use: { ...devices['Desktop Firefox'] },
    },
    {
      name: 'webkit',
      use: { ...devices['Desktop Safari'] },
    },
    /* 移动端 */
    {
      name: 'Mobile Chrome',
      use: { ...devices['Pixel 5'] },
    },
    {
      name: 'Mobile Safari',
      use: { ...devices['iPhone 12'] },
    },
  ],

  /* 开发服务器 */
  webServer: {
    command: 'npm run dev',
    url: 'http://localhost:3000',
    reuseExistingServer: !process.env.CI,
    timeout: 120 * 1000,
  },
});
