# 폐쇄망(closed-network) 운영 원칙

이 프로젝트의 프론트엔드는 최종적으로 인터넷이 차단된 폐쇄망 환경에 배포된다. 스캐폴딩 시점부터 유지해 온 원칙이며, 새 의존성이나 라이브러리를 추가할 때마다 이 기준으로 검토한다.

## 원칙

1. **외부 폰트 미사용** — `next/font/google` 등 빌드/런타임에 외부에서 폰트를 fetch하는 방식은 금지. 시스템 폰트(`-apple-system`, `Segoe UI`, `Noto Sans KR`, `맑은 고딕` 등)만 사용한다. (`src/app/globals.css`의 `--font-sans` / `--font-mono` 참고)
2. **외부 CDN 미사용** — 스크립트/스타일시트를 CDN에서 로드하지 않는다. 필요한 라이브러리는 npm 의존성으로 번들에 포함시킨다.
3. **런타임에 원격 리소스를 호출하는 라이브러리는 도입 전 반드시 검증** — 설치 시점(postinstall)뿐 아니라 런타임에도 하드코딩된 외부 URL이 없는지 확인한다. (예: shadcn CLI의 `ui.shadcn.com`, Vercel AI SDK의 `@ai-sdk/gateway` → `ai-gateway.vercel.sh` 등. 실제로 사용하지 않는 provider/게이트웨이 코드 경로는 문제 없음.)
4. **마크다운 렌더러 등 흔한 라이브러리도 자체 구현 우선 검토** — `src/components/chat/markdown.tsx`는 외부 라이브러리(remark 등) 대신 직접 구현한 최소 뷰어다. 의존성 트리가 커지고 폐쇄망 반입 대상이 늘어나는 것을 피하기 위함.
5. **LLM 호출은 백엔드를 경유** — 프론트엔드(`ai` SDK 등)는 사내 백엔드 API만 호출한다. 외부 LLM provider(OpenAI/Anthropic 등)를 프론트에서 직접 호출하지 않는다. 현재 백엔드는 개발 단계라 OpenRouter를 임시로 사용 중이며, 폐쇄망 반입 시 로컬 LLM 엔드포인트로 교체 예정이다 (백엔드 측 `core/config.py` 및 `agent/agent.py`의 `agent_provider_env()` 참고).

## 의존성 도입 시 체크리스트

새 npm 패키지나 CLI 도구를 추가하기 전에 확인한다.

1. **설치 방식이 순수 npm인가, 아니면 별도 레지스트리/CDN에서 코드를 받아오는가?**
   - 순수 npm 패키지 → 사내 레지스트리(Nexus/Artifactory 등) 미러링만 되면 문제 없음
   - shadcn/ui처럼 CLI가 자체 레지스트리에서 소스를 fetch하는 방식 → 인터넷 환경에서 미리 받아 커밋해두고, 폐쇄망에는 CLI 실행 없이 반입 ([decisions.md#shadcnui-도입](./decisions.md#shadcnui-도입) 참고)

2. **postinstall/preinstall 스크립트가 외부 리소스(바이너리, 폰트 등)를 받아오는가?**
   ```bash
   node -e "console.log(require('./node_modules/<pkg>/package.json').scripts)"
   ```

3. **번들된 코드 안에 하드코딩된 외부 URL이 있는가?**
   ```bash
   grep -rEo 'https?://[a-zA-Z0-9._-]+' node_modules/<pkg>/dist | sort -u
   ```
   찾은 도메인이 실제로 이 프로젝트가 사용하는 코드 경로에서 호출되는지 확인한다 (import는 됐지만 실제 사용하지 않는 하위 모듈이면 문제 없음).

4. **`npm run build`를 오프라인 조건으로 재현해서 실패하는지 확인** — 가장 확실한 검증. 네트워크를 끊거나 `/etc/hosts`로 의심 도메인을 막고 빌드해본다.

## 실제 발견 사례

- shadcn init이 `next/font/google`(Geist)을 자동으로 `layout.tsx`에 추가 → 빌드 시 `Unknown font 'Geist'`로 즉시 실패 확인, 제거함. ([decisions.md#shadcnui-도입](./decisions.md#shadcnui-도입))
- `@ai-sdk/gateway` 패키지에 `https://ai-gateway.vercel.sh`가 기본 baseURL로 하드코딩되어 있음을 확인. 현재 프로젝트 코드는 이 provider를 import/사용하지 않으므로 실제 호출 경로에는 들어가지 않음 — 다만 향후 `ai` SDK 사용 코드를 작성할 때 `@ai-sdk/gateway`가 아니라 사내 백엔드로 향하는 커스텀 fetch/provider를 쓰도록 주의해야 한다.
