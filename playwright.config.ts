import { defineConfig, devices } from '@playwright/test';

/**
 * Playwright E2E Testing Configuration
 * @see https://playwright.dev/docs/test-configuration
 */
export default defineConfig({
  // Test directory
  testDir: './e2e',

  // Maximum time one test can run
  timeout: 30 * 1000,

  // Test execution settings
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,

  // Reporter configuration
  reporter: [
    ['html'],
    ['list'],
    ['junit', { outputFile: 'test-results/junit.xml' }],
  ],

  // Shared test configuration
  use: {
    // Base URL for tests
    baseURL: 'http://localhost:5173',

    // Collect trace on failure
    trace: 'on-first-retry',

    // Screenshot on failure
    screenshot: 'only-on-failure',

    // Video on failure
    video: 'retain-on-failure',

    // Timeout for actions
    actionTimeout: 10 * 1000,

    // Timeout for navigation
    navigationTimeout: 30 * 1000,
  },

  // Configure projects for different browsers
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

    // Mobile browsers
    {
      name: 'Mobile Chrome',
      use: { ...devices['Pixel 5'] },
    },

    {
      name: 'Mobile Safari',
      use: { ...devices['iPhone 13'] },
    },

    // iPad (important for this project)
    {
      name: 'iPad',
      use: { ...devices['iPad Pro'] },
    },
  ],

  // Web server configuration
  webServer: [
    {
      command: 'cd web-client && npm run dev',
      url: 'http://localhost:5173',
      timeout: 120 * 1000,
      reuseExistingServer: !process.env.CI,
    },
    {
      command: 'cd voice_service && .venv/Scripts/python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8008 --app-dir voice_service',
      url: 'http://localhost:8008/health',
      timeout: 120 * 1000,
      reuseExistingServer: !process.env.CI,
    },
  ],

  // Output directory
  outputDir: 'test-results/',
});
