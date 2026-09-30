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
- chat SSE, 취소, retry, 편집·재생성, tool card와 flat `present_*` 결과 UI 조회를 확인한다.
- Backend의 CORS origin과 credential 설정이 Frontend 주소와 일치해야 한다.
- browser Network 탭이나 사내 proxy 로그에서 허용된 Backend 외 outbound 요청이
  없어야 한다.

## 현재 확인된 주의점

- shadcn 초기화는 font나 registry 의존 설정을 자동 추가할 수 있으므로 생성 결과를
  그대로 반입하지 않는다.
- AI SDK gateway는 외부 endpoint 기본값을 포함할 수 있어 의존성에서 제거했다.
- assistant-ui는 `useRemoteThreadListRuntime`(메모리 adapter) + `useLocalRuntime` 경로만 사용한다. 설치 트리에 cloud
  관련 코드가 있어도 production bundle과 runtime network에 포함되지 않는지 새 버전마다
  다시 확인한다.
- native package가 준비 환경과 폐쇄망의 OS·CPU에 맞지 않으면 설치 또는 build가
  실패하므로 `node_modules` 복사보다 사내 registry를 통한 재설치를 우선한다.

## 현재 패키지 반입 기준

- 정확한 직접·전이 의존성 버전은 `package-lock.json`을 기준으로 미러링한다.
  결과 인자 검증에는 `zod`, 표와 차트에는 `@tanstack/react-table`·`recharts`를 쓴다.
- `@assistant-ui/react-generative-ui`와 legacy chart marker용 코드는 현재 반입 대상이
  아니다. 결과 표시에는 flat `present_*` Tool UI를 쓴다.
- `@tanstack/react-table`·`recharts`의 MIT 고지는
  `public/table-chart-license-notices.txt`에 유지한다. 배포 시 이 파일을 포함한다.
- 사내 registry가 패키지를 실제 보관하는지 확인한 뒤, 비어 있는 npm cache로
  `npm ci`와 `npm run build`를 수행한다. 외부 proxy 조회 성공만으로 반입 완료를
  판단하지 않는다.

현재 아키텍처·UI 결정은 [Frontend 진행 중·현재 계약](../plan/InProgress.md)을 따른다.
API 서버와 Agent SDK의 반입·운영은 Frontend workspace 범위가 아니며,
운영자가 제공한 배포 절차와 확정된 API 주소만 사용한다.
