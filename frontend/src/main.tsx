/**
 * Vite 엔트리. Next App Router 의 `app/layout.tsx` 역할을 대신한다.
 *   - <html lang="ko"> 와 <head> 메타는 index.html 로 옮겼다
 *   - globals.css 는 src/app/ 에 그대로 두고 여기서 import 한다
 *     (tailwind.config.ts 를 가리키는 @config 상대경로를 깨뜨리지 않기 위함)
 *   - next.config.mjs 의 reactStrictMode: true 를 <React.StrictMode> 로 대체
 */

import React from "react";
import ReactDOM from "react-dom/client";

import "./app/globals.css";
import App from "./App";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
