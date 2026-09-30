# Frontend 폐쇄망 반입·운영 지침

Frontend는 외부 인터넷 없이 설치·빌드·실행할 수 있어야 한다. 패키지나 UI
도구를 추가할 때는 이 문서의 준비, 반입, 설치와 검증 절차를 함께 갱신한다.

## 운영 원칙

- 외부 font, CDN script·stylesheet, image와 telemetry를 사용하지 않는다.
- 브라우저는 사내 Backend만 호출하며 외부 LLM provider에 직접 연결하지 않는다.
- 모든 runtime 라이브러리는 npm bundle에 포함한다.
- shadcn과 assistant-ui Elements처럼 별도 registry에서 소스를 받는 CLI는 인터넷 환경에서
  미리 실행하고 생성 소스를 commit한다. 폐쇄망에서는 해당 CLI fetch를 실행하지 않는다.
- package와 lockfile은 함께 반입하고 설치할 때 lockfile 버전을 기준으로 한다.
- Nexus URL, 인증 token과 사내 도메인은 저장소에 기록하지 않고 폐쇄망 환경에서
  로컬 npm 설정과 `.env.local`로 주입한다.

## 인터넷 환경에서 준비

1. `package.json`과 lockfile이 일치하는지 확인한다.
2. 사내 npm registry에 정확한 버전과 모든 전이 의존성이 있는지 확인한다.
3. registry에 없는 패키지는 사내 반입 승인을 거쳐 tarball로 준비하거나 미러링한다.
4. 대상 폐쇄망과 같은 OS·CPU에서 필요한 native optional package를 확인한다.
   Vite build에는 esbuild와 Rollup의 플랫폼별 패키지가 필요할 수 있다.
5. 깨끗한 cache와 lockfile로 설치·빌드한다.

```bash
cd frontend
npm ci
npm run build
npm run lint
```

사내 registry가 아직 없다면 승인된 임시 npm cache 또는 tarball 묶음을 만든다.
`node_modules` 자체 반입은 OS·Node.js·package manager 버전이 완전히 같을 때만
대안으로 사용한다.

## 패키지 도입 점검

새 패키지마다 다음을 확인한다.

```bash
npm view <package>@<version> dependencies optionalDependencies peerDependencies
node -e "console.log(require('./node_modules/<package>/package.json').scripts)"
grep -rEo 'https?://[a-zA-Z0-9._-]+' node_modules/<package>/dist | sort -u
```

- preinstall/postinstall에서 binary, font나 model을 내려받는지 확인한다.
- hardcoded URL이 실제 실행 경로에서 fetch되는지 bundle과 코드로 확인한다.
- `npm run build` 이후 `dist/`의 URL을 검사한다. 문서 링크나 XML namespace 문자열과
  실제 network 호출을 구분한다.
- 새 package가 없어도 CLI가 자동으로 dependency, font나 config를 추가할 수 있으므로
  실행 직후 diff를 검토한다.

## 폐쇄망으로 이전

1. 검토된 source archive와 `package.json`, lockfile, 필요한 package tarball 또는
   registry 목록을 보안 반입 절차로 옮긴다.
2. `.env.local`, npm token과 내부 URL은 source와 별도 승인 채널로 전달한다.
3. 폐쇄망의 Node.js와 npm 버전을 준비 환경과 맞춘다.
4. 사내 registry 또는 오프라인 cache만 사용해 설치한다.

```bash
cd frontend
npm config set registry <INTERNAL_NPM_REGISTRY>
npm ci --offline
cp .env.example .env.local
npm run build
```

`npm ci --offline`을 지원할 cache가 없고 사내 registry를 사용한다면 `--offline`은
생략하되 방화벽 로그로 외부 접속이 발생하지 않는지 확인한다. 실제 registry 주소는
명령 이력 공유나 문서에 남기지 않는다.

## 기동과 인수 검증

```bash
npm run preview
```

- `dist/`가 3100 포트에서 열리고 외부 font·asset 요청이 없어야 한다.
- `.env.local`의 `VITE_API_BASE_URL`이 폐쇄망 Backend를 가리켜야 한다.
- chat SSE, 취소, retry, 편집·재생성, tool card와 standalone 차트 Tool UI 및
  과거 chart marker 조회를 확인한다.
- Backend의 CORS origin과 credential 설정이 Frontend 주소와 일치해야 한다.
- browser Network 탭이나 사내 proxy 로그에서 허용된 Backend 외 outbound 요청이
  없어야 한다.

## 2026-09-22 반입 항목: 결과 Tool UI

- `zod@4.6.5`를 결과 Tool 인자 검증용 직접 의존성으로 고정한다.
- `@assistant-ui/react-generative-ui`는 flat `present_*` Tool 전환 후 제거했다.
- 사내 registry에는 현재 `package-lock.json`의 정확한 버전과 전이 의존성만 반입한다.
  `npm view <package>@<version> dependencies peerDependencies`와 `dist` URL grep 절차를 따른다.

## 현재 확인된 주의점

- shadcn 초기화는 font나 registry 의존 설정을 자동 추가할 수 있으므로 생성 결과를
  그대로 반입하지 않는다.
- AI SDK gateway는 외부 endpoint 기본값을 포함할 수 있어 의존성에서 제거했다.
- assistant-ui는 `useRemoteThreadListRuntime`(메모리 adapter) + `useLocalRuntime` 경로만 사용한다. 설치 트리에 cloud
  관련 코드가 있어도 production bundle과 runtime network에 포함되지 않는지 새 버전마다
  다시 확인한다.
- native package가 준비 환경과 폐쇄망의 OS·CPU에 맞지 않으면 설치 또는 build가
  실패하므로 `node_modules` 복사보다 사내 registry를 통한 재설치를 우선한다.

관련 아키텍처 결정은 [Frontend 기술 결정 기록](decisions.md)을 따른다.
API 서버와 Agent SDK의 반입·운영은 Frontend workspace 범위가 아니며,
운영자가 제공한 배포 절차와 확정된 API 주소만 사용한다.

## 2026-09-16 Elements 반입

공식 registry의 Thread, ThreadList, ToolCall, AgentPlan, TooltipIconButton을
준비 환경에서 검토해 `src/components/assistant-ui/elements`에 조정 소스로
포함했다. 출처·수정 범위는 같은 폴더의 `README.md`, MIT 고지는 상위
`LICENSE`에 있다. 기존 MarkdownText도 이 디렉터리로 이동했다.
package.json과 lockfile은 변경하지 않았고 신규 npm 의존성은 없다.
`components.json`의 registry URL은 개발 시 소스 생성용이며 앱이 호출하지 않는다.


### 공식 CLI 설치 후속

사용자 요청으로 tw-shimmer 0.4.13과 zustand 5.0.15를 직접 의존성에 고정했다.
신규 tarball은 tw-shimmer 하나이며 zustand는 이미 잠긴 전이 의존성과 동일하다.
두 패키지에 설치 스크립트·런타임 외부 fetch는 없고 tw-shimmer는 로컬 CSS다.
사내 registry 확보 여부는 이 환경에서 확인할 수 없으므로 반입 시 위 준비 절차에
따라 정확한 버전을 미러링해야 한다. 기존 package 버전은 변경하지 않았다.

## 2026-09-16 TanStack Table·Recharts 점검

대화형 표는 `@tanstack/react-table` 9.2.4, 차트는 `recharts` 3.8.0을 사용한다.
두 직접 의존성은 `package.json`과 lockfile에 정확한 버전으로 고정했다. TanStack
Table의 잠긴 전이 의존성은 `@tanstack/table-core` 9.2.4,
`@tanstack/react-store` 0.11.1, `@tanstack/store` 0.11.1이다.

두 프로젝트는 MIT 라이선스다. 사내 업무, 상업적 사용, 수정과 재배포가 가능하며,
복사본 또는 중요한 부분에 저작권 및 허가 고지를 보존해야 한다. 무보증 조건도
함께 적용된다. 앱은 두 라이브러리를 번들에 포함하며 CDN이나 외부 runtime API를
호출하지 않는다. 배포물에 포함되는 전문은
`public/table-chart-license-notices.txt`에서 관리한다. 회사의 별도 오픈소스 승인
절차가 있으면 이 기술·라이선스 점검과 별도로 따른다.

현재 개발 환경의 npm registry는 공개 npm을 가리키므로 사내 Nexus에 패키지가
있는지는 여기서 확인하지 못했다. Nexus에 접근할 수 있는 준비 환경에서 실제 주소를
환경 변수로만 주입한 뒤 정확한 버전을 조회한다.

```bash
cd frontend
export INTERNAL_NPM_REGISTRY='<NEXUS_NPM_REGISTRY>'

npm view @tanstack/react-table@9.2.4 version license dependencies \
  --registry="$INTERNAL_NPM_REGISTRY"
npm view @tanstack/table-core@9.2.4 version license dependencies \
  --registry="$INTERNAL_NPM_REGISTRY"
npm view @tanstack/react-store@0.11.1 version license dependencies \
  --registry="$INTERNAL_NPM_REGISTRY"
npm view @tanstack/store@0.11.1 version license dependencies \
  --registry="$INTERNAL_NPM_REGISTRY"
npm view recharts@3.8.0 version license dependencies optionalDependencies \
  --registry="$INTERNAL_NPM_REGISTRY"
```

각 명령이 요청한 버전을 출력하면 직접 패키지는 조회 가능한 상태다. Nexus의 group
repository가 외부 proxy를 허용하는 환경이라면 조회 성공만으로 사전 반입 완료를
뜻하지 않을 수 있다. Nexus UI에서 artifact가 hosted 또는 cache에 실제 저장됐는지
함께 확인한다.

모든 전이 의존성과 OS별 optional package까지 확인하려면 깨끗한 checkout에서 빈
cache로 lockfile 설치를 실행한다. 이 검증이 성공해야 폐쇄망 설치 가능 판정을 내린다.

```bash
cd frontend
NPM_AUDIT_CACHE="$(mktemp -d)"
npm ci --registry="$INTERNAL_NPM_REGISTRY" --cache="$NPM_AUDIT_CACHE" --prefer-online
npm ls @tanstack/react-table @tanstack/table-core @tanstack/react-store \
  @tanstack/store recharts
npm run build
rm -rf "$NPM_AUDIT_CACHE"
```

인증 token과 실제 Nexus URL은 `.npmrc`, shell history, 빌드 로그와 저장소에 남기지
않는다. `npm ci`가 404로 실패하면 오류에 나온 정확한 package와 버전을 Nexus에
미러링한 뒤 빈 cache 검증을 다시 수행한다.
