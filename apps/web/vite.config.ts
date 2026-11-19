import {defineConfig} from "vite";

export default defineConfig({
  server: {
    host: "127.0.0.1",
    proxy: {"/api": process.env.RESOURCE_BASE_URL || "http://127.0.0.1:8000"},
  },
});
