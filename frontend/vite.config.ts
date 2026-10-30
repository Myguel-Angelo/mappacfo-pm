import path from "node:path";
import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// O navegador só fala com o Vite; /api é repassado ao Django (mesma origem: cookie de
// sessão e CSRF funcionam sem CORS). No container, API_PROXY_TARGET aponta para o serviço api.
const apiProxy = process.env.API_PROXY_TARGET ?? "http://localhost:8000";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: { "@": path.resolve(import.meta.dirname, "./src") },
  },
  server: {
    host: true,
    port: 5173,
    strictPort: true,
    // Sem changeOrigin: o Django recebe Host localhost:5173 e o Origin do navegador bate.
    proxy: { "/api": apiProxy },
    // Bind mount do Windows não propaga eventos de arquivo para o container.
    watch: { usePolling: process.env.VITE_USE_POLLING === "true" },
  },
});
