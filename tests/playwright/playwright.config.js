// @ts-check
const { defineConfig } = require('@playwright/test');

/**
 * Playwright configuration for SHT31 API testing.
 * @see https://playwright.dev/docs/test-configuration
 */
module.exports = defineConfig({
  testDir: './',
  testMatch: '**/*.spec.js',
  
  /* Run tests in files in parallel */
  fullyParallel: true,
  
  /* Fail the build on CI if you accidentally left test.only in the source code */
  forbidOnly: !!process.env.CI,
  
  /* Retry on CI only */
  retries: process.env.CI ? 2 : 0,
  
  /* Reporter to use */
  reporter: [
    ['html', { outputFolder: 'playwright-report' }],
    ['json', { outputFile: 'test-results.json' }],
    ['junit', { outputFile: 'test-results.xml' }],
    ['list']
  ],
  
  /* Shared settings for all the projects below */
  use: {
    /* Base URL for the SHT31 Flask server */
    baseURL: process.env.SHT31_BASE_URL || 'http://127.0.0.1:5000',
    
    /* Collect trace when retrying the failed test */
    trace: 'on-first-retry',
  },

  /* Configure projects for API testing */
  projects: [
    {
      name: 'api-tests',
    },
  ],

  /* Configure timeout */
  timeout: 30000,
  expect: {
    timeout: 10000,
  },

  /* Global setup and teardown for server management */
  globalSetup: require.resolve('./global-setup.js'),
  globalTeardown: require.resolve('./global-teardown.js'),
});
