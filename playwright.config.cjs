// Webbläsartester (Playwright). Kör: npx playwright test
const { defineConfig, devices } = require("@playwright/test");

module.exports = defineConfig({
  testDir: "tester/webblasare",
  globalSetup: "./tester/webblasare/forbered.cjs",
  timeout: 30_000,
  fullyParallel: true,
  reporter: process.env.CI ? [["list"], ["github"]] : "list",
  use: { baseURL: "http://127.0.0.1:8799", trace: "retain-on-failure" },
  webServer: {
    command: "python3 -m http.server 8799 --bind 127.0.0.1",
    url: "http://127.0.0.1:8799/index.html",
    reuseExistingServer: !process.env.CI,
  },
  projects: [
    { name: "dator", use: { ...devices["Desktop Chrome"] } },
    { name: "mobil", use: { ...devices["Pixel 7"] } },
  ],
});
