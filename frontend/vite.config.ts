import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import pkg from "./package.json";

// The backend allows http://localhost:5173 in CORS_ALLOWED_ORIGINS.
export default defineConfig({
  plugins: [react()],
  // strictPort: fail instead of silently moving to 5174, which CORS would then reject.
  server: { port: 5173, strictPort: true },
  define: { __APP_VERSION__: JSON.stringify(pkg.version) },
});
