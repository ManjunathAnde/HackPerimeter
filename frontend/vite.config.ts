import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// envDir points at the repo root so frontend and backend share one .env
export default defineConfig({
  plugins: [react()],
  envDir: "..",
  server: { port: 5173 },
});
