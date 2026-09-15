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
npm run build
npm run lint
npm run preview
```

## 참고

- [Frontend 작업 지침](AGENTS.md)
- [기술 결정 기록](docs/decisions.md)
- [폐쇄망 운영 원칙](docs/closed-network.md)
- [Frontend 실행 계획](plan/)
- [전체 기능 계획](../plan/)
