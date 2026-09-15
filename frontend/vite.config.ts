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
  // host: true 로 0.0.0.0 바인딩 — SSH 원격 개발(Cursor Remote-SSH 등)에서
  // 클라이언트가 127.0.0.1 이 아닌 주소로 접속해도(포트 포워딩 경유) 붙을 수 있어야 한다.
  server: { port: 3000, strictPort: true, host: true },
  preview: { port: 3000, strictPort: true, host: true },
  build: {
    sourcemap: false,
  },
});
