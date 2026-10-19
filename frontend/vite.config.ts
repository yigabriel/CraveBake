import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import pkg from "./package.json";

// The backend allows http://localhost:5173 in CORS_ALLOWED_ORIGINS.
export default defineConfig({
  plugins: [react()],
  server: { port: 5173 },
  define: { __APP_VERSION__: JSON.stringify(pkg.version) },
});
