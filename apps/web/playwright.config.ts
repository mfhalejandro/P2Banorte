import {defineConfig} from "@playwright/test";

export default defineConfig({
  testDir: "./tests",
  workers: 1,
  use: {
    baseURL: "http://127.0.0.1:5179",
    launchOptions: {executablePath: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE},
  },
  webServer: [
    {command: "PYTHONPATH=. .venv/bin/python -B tests/p0/smoke_server.py", cwd: "../..",
     url: "http://127.0.0.1:8179/api/health"},
    {command: "npm run dev -- --port 5179 --strictPort", env: {RESOURCE_BASE_URL: "http://127.0.0.1:8179"},
     url: "http://127.0.0.1:5179"},
  ],
});
