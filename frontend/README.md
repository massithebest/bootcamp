# Production Planning Agent Frontend

Backend의 SSE `AgentEvent`를 표시하는 Vite 7·React 18·TypeScript 기반 3-pane
워크벤치다. Backend는 기본적으로 `http://localhost:8000`, Frontend는
`http://localhost:3000`을 사용한다.

## 설치와 실행

```bash
npm install
cp .env.example .env.local
npm run dev
```

`.env.local`의 `VITE_API_BASE_URL`을 Backend 주소로 설정한다.

## 검증

```bash
npm test
npm run build
npm run lint
npm run preview
```

`npm test`는 Node 내장 테스트 실행기와 설치된 Vite/TypeScript로 SSE 파서·전송,
메시지 상태 전이와 결과 렌더링을 검증한다. 추가 테스트 패키지는 필요 없다.
개발 서버의 `/tests/chat-browser.html`은 실제 React StrictMode와 assistant-ui
runtime으로 retry/cancel/edit/regenerate를 검증한다. 요청은 해당 테스트 페이지
안에서만 mock 처리하며 결과와 PASS/FAIL을 표시한다. production build에는 포함하지 않는다.

## 참고

- [Frontend 작업 지침](AGENTS.md)
- [기술 결정 기록](docs/decisions.md)
- [폐쇄망 운영 원칙](docs/closed-network.md)
- [Frontend 실행 계획](plan/)
- [전체 기능 계획](../plan/)
