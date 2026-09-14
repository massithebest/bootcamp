import { fileURLToPath, URL } from "node:url";

import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  // FastAPI StaticFiles 마운트 지점이 아직 미정이라 상대 경로로 둔다.
  // 클라이언트 라우터가 없으므로 루트든 서브패스든 그대로 동작한다.
  base: "./",
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url)),
    },
  },
  // 백엔드 CORS_ALLOW_ORIGINS 기본값(localhost:3000)을 그대로 쓰기 위해
  // dev/preview 둘 다 3000 에 고정한다. 다른 포트로 밀리면 조용히 CORS 가 깨진다.
  server: { port: 3000, strictPort: true },
  preview: { port: 3000, strictPort: true },
  build: {
    sourcemap: false,
  },
});
