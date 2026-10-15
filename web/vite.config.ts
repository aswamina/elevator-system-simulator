import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

// `npm run dev` serves the app on :5173 and forwards API calls to the
// simulator on :8000; `npm run build` writes dist/, which api.py serves at /.
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/api": "http://127.0.0.1:8000",
      "/health": "http://127.0.0.1:8000",
    },
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["src/test-setup.ts"],
  },
});
