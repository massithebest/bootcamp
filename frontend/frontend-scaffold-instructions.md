# Production Planning Agent Frontend 스캐폴딩 구축

## 목표

Claude Agent SDK 기반 생산계획 Agent Backend와 통신하는 질의응답형 Frontend의 기본 스캐폴딩을 구축한다.

현재 단계에서는 완성된 UI나 복잡한 업무 화면을 만드는 것이 목적이 아니다.

다음을 중심으로 구현한다.

- Next.js 기반 기본 구조
- Chat UI 기본 구조
- FastAPI `/api/chat` 연동 구조
- SSE Streaming 처리
- Backend `AgentEvent` 렌더링 구조
- Tool Result 확장 구조
- 폐쇄망 환경 대응
- 최소 Dependency 원칙
- Vercel AI SDK Optional 적용

구체적인 내부 구현 코드는 현재 프로젝트의 Next.js 버전과 설치된 Dependency를 확인한 후 적절하게 작성한다.

---

# 1. 프로젝트 위치

전체 프로젝트는 단일 Repository를 사용한다.

```text id="uv69fo"
production-planning-agent/
├── frontend/
├── backend/
├── docs/
└── README.md
```

이번 작업 범위는 `frontend/`이다.

---

# 2. 기본 기술 구성

기본 기술은 다음과 같다.

```text id="tysiwt"
Next.js
React
TypeScript
Tailwind CSS
```

추가적으로 Vercel AI SDK는 현재 환경에 존재하는 경우에만 사용한다.

```text id="577ymw"
ai
@ai-sdk/react
```

Vercel AI SDK가 없으면 신규 설치를 강제하지 않는다.

대신 Browser / React 기본 기능으로 Streaming Chat을 구현한다.

---

# 3. Vercel AI SDK 적용 원칙

먼저 현재 프로젝트의 `package.json`과 사용 가능한 사내 Package를 확인한다.

다음 패키지가 이미 사용 가능하면:

```text id="ycyu4s"
ai
@ai-sdk/react
```

Vercel AI SDK를 활용하는 방향을 우선 검토한다.

가능하면 다음 역할에 사용한다.

```text id="r9k4ly"
채팅 Message 상태 관리
Streaming 응답 관리
Chat Request 관리
Abort / Loading 상태 관리
```

단, Vercel AI SDK를 사용하더라도 다음 외부 서비스는 사용하지 않는다.

```text id="d6trjr"
Vercel AI Gateway
Vercel Analytics
Vercel Telemetry
외부 Model Provider API
```

LLM 및 Agent 실행은 Frontend에서 수행하지 않는다.

```text id="eguf3o"
Frontend
   ↓
FastAPI
   ↓
Claude Agent SDK
```

구조를 유지한다.

---

# 4. Vercel AI SDK가 없는 경우

`ai`, `@ai-sdk/react`가 사용할 수 없는 경우 신규 Package 설치를 시도하지 않는다.

다음 기본 기능을 사용한다.

```text id="u4fstq"
React useState
React useRef
fetch
ReadableStream
TextDecoder
AbortController
```

FastAPI `/api/chat` SSE Stream을 직접 처리한다.

중요한 것은 AI SDK 사용 여부와 관계없이 Frontend Component와 Backend API Contract가 동일하게 유지되는 것이다.

---

# 5. shadcn/ui 사용 금지

shadcn CLI 및 외부 Component Registry를 사용하지 않는다.

다음 명령을 사용하지 않는다.

```text id="wfpm0m"
npx shadcn init
npx shadcn add
```

UI는 기본적으로 다음 조합으로 구현한다.

```text id="af73tt"
React
HTML
Tailwind CSS
```

필요한 Button, Input, Card, Badge 등의 기본 요소는 직접 작성한다.

UI Component Library를 추가로 설치하지 않는다.

---

# 6. Frontend 폴더 구조

다음 구조를 기준으로 생성한다.

```text id="xwebxy"
frontend/
├── src/
│   ├── app/
│   │   ├── layout.tsx
│   │   ├── page.tsx
│   │   └── globals.css
│   │
│   ├── components/
│   │   └── chat/
│   │       ├── chat-window.tsx
│   │       ├── message-bubble.tsx
│   │       ├── message-input.tsx
│   │       ├── status-card.tsx
│   │       └── tool-result-card.tsx
│   │
│   ├── lib/
│   │   └── chat-api.ts
│   │
│   └── types/
│       └── chat.ts
│
├── .env.local
├── package.json
└── tsconfig.json
```

현재 단계에서는 불필요하게 폴더를 세분화하지 않는다.

다음 구조는 아직 만들지 않는다.

```text id="pxyt8o"
hooks/
store/
providers/
features/
repositories/
services/
```

실제 필요성이 생겼을 때 추가한다.

---

# 7. 전체 Frontend 처리 흐름

Frontend는 다음 구조를 따른다.

```text id="03n9h1"
User
 ↓
MessageInput
 ↓
ChatWindow
 ↓
Chat API / Transport
 ↓
POST /api/chat
 ↓
SSE
 ↓
AgentEvent
 ↓
ChatWindow
 ↓
Message / Status / Tool Result
```

Frontend는 Claude Agent SDK 내부 Event를 직접 처리하지 않는다.

Backend에서 변환된 `AgentEvent`만 처리한다.

---

# 8. Backend API Contract

Frontend는 다음 Backend API를 사용한다.

```text id="0usgrp"
POST /api/chat
```

기본 요청 값:

```text id="5tni91"
message
conversation_id
```

개념적으로 다음 형태를 따른다.

```text id="70qbei"
{
  message: string
  conversation_id?: string
}
```

`conversation_id`는 사용자 관점의 대화 식별자이다.

Claude Agent SDK 내부 Session ID와 동일한 개념으로 취급하지 않는다.

---

# 9. AgentEvent Type

Backend와 동일한 Event Contract를 Frontend에 정의한다.

지원 Event Type:

```text id="9g7394"
text
status
tool_call
tool_result
error
done
```

각 역할:

| Event | Frontend 역할 |
|---|---|
| `text` | Assistant 응답 표시 |
| `status` | 현재 업무 진행 상태 표시 |
| `tool_call` | Tool 실행 시작 상태 관리 |
| `tool_result` | Tool 결과 UI 표시 |
| `error` | 사용자 오류 메시지 표시 |
| `done` | Streaming 종료 |

Frontend Type은 Backend `api/schemas.py`의 `AgentEvent`와 가능한 한 동일한 Contract를 유지한다.

---

# 10. Chat Message 구조

Frontend에서는 사용자 메시지와 Assistant 메시지를 별도의 Chat Message 개념으로 관리한다.

Assistant Message에는 최소한 다음 정보를 담을 수 있도록 한다.

```text id="obik4z"
content
statuses
toolResults
```

개념적으로:

```text id="invbam"
Assistant Message
 ├─ Text
 ├─ Status
 └─ Tool Results
```

구조이다.

Agent 내부 Reasoning이나 Chain-of-Thought를 저장하거나 표시하지 않는다.

---

# 11. ChatWindow

`chat-window.tsx`는 전체 Chat UI와 Message 상태를 관리한다.

주요 역할:

```text id="5s4hqb"
사용자 Message 추가
Assistant Message 생성
Backend Streaming 요청
AgentEvent 수신
Message 상태 업데이트
Loading 관리
Error 처리
```

사용자가 질문을 보내면 다음 흐름으로 처리한다.

```text id="8dsl9s"
1. 사용자 Message 추가

2. Assistant Message Placeholder 생성

3. Backend /api/chat 호출

4. AgentEvent Streaming 수신

5. Event Type별 Assistant Message 업데이트

6. done 수신

7. Streaming 상태 종료
```

---

# 12. Event 처리 방식

## text

Assistant Message의 Text에 순차적으로 반영한다.

```text id="kz5z0v"
text delta
 ↓
Assistant content
```

Streaming되는 Text가 자연스럽게 이어지도록 한다.

---

## status

Agent 업무 진행 상태를 표시한다.

예:

```text id="3rh6nx"
[완료] 요청 분석
[완료] 생산 실적 조회
[진행] Simulation 수행
[대기] 결과 분석
```

같은 `step`에 대한 새로운 Event가 들어오면 기존 Status를 업데이트할 수 있는 구조로 만든다.

기본 Status:

```text id="2wd9ha"
pending
running
completed
error
```

---

## tool_call

현재 단계에서는 Tool 이름과 실행 상태를 내부적으로 관리할 수 있도록 한다.

필요하면 Status UI에 반영한다.

Tool Call 자체를 복잡한 카드로 표시할 필요는 없다.

---

## tool_result

Assistant Message의 Tool Result 목록에 추가한다.

Tool Result는 `tool-result-card.tsx`를 통해 렌더링한다.

---

## error

사용자가 이해할 수 있는 오류 메시지를 표시한다.

내부 Exception이나 Stack Trace를 UI에 표시하지 않는다.

---

## done

현재 Streaming 응답을 종료한다.

Loading 상태도 종료한다.

---

# 13. MessageBubble

`message-bubble.tsx`는 사용자와 Assistant Message를 구분해 표시한다.

기본 배치:

```text id="as1nxk"
Assistant → 왼쪽
User      → 오른쪽
```

Assistant Message는 다음 순서로 표현할 수 있도록 한다.

```text id="bucipz"
Status
 ↓
Text
 ↓
Tool Result
```

초기에는 복잡한 Markdown Renderer를 사용하지 않는다.

일반 Text와 줄바꿈 정도만 안정적으로 표현한다.

---

# 14. MessageInput

`message-input.tsx`는 사용자 입력을 담당한다.

기본 기능:

```text id="13fnd1"
텍스트 입력
Enter 전송
전송 Button
빈 메시지 방지
Streaming 중 중복 전송 방지
```

가능하면 `<textarea>`를 사용하여 향후 여러 줄 질문도 받을 수 있도록 한다.

초기에는 파일 첨부, 음성 입력, 자동완성 기능을 만들지 않는다.

---

# 15. StatusCard

`status-card.tsx`는 Agent의 업무 실행 상태를 표현한다.

초기에는 Text 중심의 단순한 UI를 만든다.

예:

```text id="pa8l82"
생산계획을 분석하고 있습니다.

완료  요청 분석
완료  생산계획 데이터 조회
진행  Simulation 수행
대기  결과 분석
```

외부 Icon Package를 사용하지 않는다.

Tailwind 스타일만 사용한다.

---

# 16. ToolResultCard

`tool-result-card.tsx`는 Agent Tool의 실행 결과를 표시한다.

초기에는 Generic Result Component로 구현한다.

예:

```text id="v47f41"
query_database

{
  ...
}
```

단, 향후 `tool_name`에 따라 전용 UI를 확장할 수 있도록 설계한다.

예:

```text id="ylcz9s"
query_database
 → DatabaseResult

search_knowledge
 → KnowledgeResult

simulate_line_capacity
 → SimulationResult

simulate_material_constraint
 → SimulationResult

simulate_line_comparison
 → ComparisonResult
```

현재는 전용 Component를 모두 구현하지 않는다.

확장하기 쉬운 분기 구조만 유지한다.

---

# 17. 향후 Tool Result UI 방향

향후 생산계획 Agent가 고도화되면 다음 형태로 확장 가능해야 한다.

```text id="6hpwfp"
SQL Result
 └─ Table

RAG Result
 └─ Document List

Simulation Result
 ├─ KPI Card
 ├─ Table
 └─ Chart

Scenario Comparison
 ├─ Comparison Table
 └─ Chart
```

현재 Skeleton에서는 JSON 또는 간단한 Text 형태까지만 구현한다.

---

# 18. Chat API / Transport

`lib/chat-api.ts`는 Backend와의 통신만 담당한다.

Component 안에 직접 SSE Parsing 코드를 길게 작성하지 않는다.

역할:

```text id="pg6pkn"
POST /api/chat
 ↓
SSE Streaming
 ↓
AgentEvent 변환
 ↓
ChatWindow 전달
```

Vercel AI SDK 사용 여부에 따라 내부 구현 방식은 달라질 수 있다.

---

# 19. AI SDK가 있는 경우

현재 설치된 Vercel AI SDK가 Backend의 Streaming Protocol과 호환 가능하다면 `useChat` 등의 기능을 활용한다.

다만 Backend의 `AgentEvent` 구조를 유지하는 것이 우선이다.

Vercel AI SDK를 사용하기 위해 Backend 전체 Event Contract를 무리하게 변경하지 않는다.

필요하다면 Adapter 또는 Transport 계층에서 변환한다.

전체 개념:

```text id="rkpxq1"
Backend AgentEvent
       ↓
Frontend Transport
       ↓
AI SDK
       ↓
Chat Component
```

---

# 20. AI SDK가 없는 경우

Browser 기본 API로 SSE Streaming을 구현한다.

필요 기능:

```text id="2rawgr"
fetch
response.body
ReadableStream
getReader
TextDecoder
AbortController
```

외부 SSE Parser Package를 추가하지 않는다.

SSE Event 경계를 안정적으로 처리하고 각 `data:` Payload를 `AgentEvent`로 변환한다.

구현 세부사항은 Claude Code가 현재 Next.js / Browser 환경에 맞게 작성한다.

---

# 21. Streaming 취소

향후 사용자가 Agent 실행을 중단할 수 있도록 `AbortController`를 사용할 수 있는 구조를 만든다.

초기 UI에 Stop 버튼을 반드시 만들 필요는 없다.

다만 Streaming API Layer가 Abort Signal을 받을 수 있도록 설계한다.

---

# 22. Conversation ID

Frontend에서 현재 대화에 대한 `conversation_id`를 관리할 수 있도록 한다.

초기 POC에서는 간단한 Client-side ID 생성으로 충분하다.

현재 단계에서는 다음 기능까지 구현하지 않는다.

```text id="0e29ou"
Conversation DB 저장
대화 목록
대화 제목 생성
History 복원
사용자별 Conversation 관리
```

향후 Backend Memory / History와 연결할 수 있는 인터페이스만 유지한다.

---

# 23. 환경변수

Backend 주소는 환경변수로 관리한다.

예:

```text id="n17p7h"
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

Backend URL을 여러 Component에 Hard Coding하지 않는다.

현재 POC에서는 Browser가 FastAPI를 직접 호출한다.

```text id="r3o7q7"
Browser
 ↓
FastAPI
```

Next.js BFF는 아직 추가하지 않는다.

---

# 24. CORS

Frontend와 Backend 개발 Server의 Port가 다르므로 Backend에서 CORS가 필요할 수 있다.

예:

```text id="hhrzxe"
Frontend
localhost:3000

Backend
localhost:8000
```

현재 Backend에 CORS 설정이 없다면 필요한 설정을 확인한다.

단, 임의로 과도하게 넓은 CORS 설정을 적용하지 않는다.

개발 환경에서 필요한 Origin만 허용하는 방향을 우선한다.

---

# 25. 폐쇄망 원칙

Frontend는 외부 인터넷 연결 없이 실행 및 Build 가능한 구조를 목표로 한다.

다음 기능을 사용하지 않는다.

```text id="tp7hnm"
Google Fonts
CDN
외부 CSS
외부 Script
외부 Image URL
Vercel AI Gateway
Vercel Analytics
외부 Telemetry
OpenAI API
Anthropic API
Google AI API
외부 Icon Service
```

Backend FastAPI 주소 외의 외부 Network 호출을 추가하지 않는다.

---

# 26. Font

`next/font/google`을 사용하지 않는다.

다음 방식 중 하나를 사용한다.

```text id="jkgwma"
System Font
또는
사내에서 이미 제공되는 Local Font
```

Font 때문에 Build 과정에서 외부 Network 요청이 발생하면 안 된다.

---

# 27. Dependency 원칙

현재 프로젝트 또는 사내 환경에서 사용 가능한 Dependency를 우선한다.

새로운 Package를 임의로 설치하지 않는다.

다음 기준을 따른다.

```text id="uf40k7"
현재 Package로 구현 가능
 → 기존 Package 사용

React / Browser 기본 기능으로 가능
 → 기본 기능 사용

신규 Package가 반드시 필요
 → 설치하지 않고 TODO와 이유 기록
```

특히 다음 Package를 임의로 추가하지 않는다.

```text id="5jih88"
shadcn
Radix UI
Axios
Zustand
Redux
SSE Parser
Markdown Renderer
Chart Library
Icon Library
```

현재 이미 설치되어 있더라도 반드시 필요한 경우에만 사용한다.

---

# 28. UI 스타일 원칙

현재는 업무 기능 검증이 목적이다.

화려한 디자인보다 다음을 우선한다.

```text id="8pdw5h"
가독성
단순함
명확한 정보 계층
업무 결과 표현 확장성
```

Tailwind를 사용하여 기본 Chat UI를 구성한다.

초기 화면은 다음 정도면 충분하다.

```text id="18f6j2"
┌────────────────────────────────────────┐
│ Production Planning Agent              │
├────────────────────────────────────────┤
│                                        │
│       Assistant Message                │
│                                        │
│                      User Message      │
│                                        │
│       Status                           │
│       Tool Result                      │
│                                        │
├────────────────────────────────────────┤
│ 질문 입력...                    [전송] │
└────────────────────────────────────────┘
```

---

# 29. 현재 구현하지 않을 UI

현재 단계에서는 다음을 구현하지 않는다.

```text id="svki37"
로그인
Sidebar
대화 목록
Dashboard
관리자 화면
파일 업로드
파일 다운로드
Markdown Editor
Chart
Simulation 전용 화면
Scenario 비교 화면
설정 화면
Dark Mode
반응형 Mobile 최적화
```

현재 목표는 Chat 기반 Agent 통신 검증이다.

---

# 30. Component 책임

각 Component의 책임을 명확하게 나눈다.

```text id="te6fkx"
ChatWindow
→ 전체 Chat 상태 / Streaming 관리

MessageBubble
→ Message 표현

MessageInput
→ 사용자 입력

StatusCard
→ Agent 진행 상태

ToolResultCard
→ Tool 결과
```

Component 간 역할을 과도하게 섞지 않는다.

---

# 31. 상태관리 원칙

현재는 React 기본 State만 사용한다.

```text id="67480m"
useState
useRef
```

정도로 충분하다.

다음 상태관리 Library는 추가하지 않는다.

```text id="hfmv0d"
Redux
Zustand
MobX
Recoil
```

대화 상태가 복잡해진 뒤 필요성을 다시 검토한다.

---

# 32. Error 처리

다음 상황을 사용자에게 적절하게 표현한다.

```text id="qvji6g"
Backend 연결 실패
HTTP 오류
SSE 오류
Agent error Event
Stream 비정상 종료
```

내부 기술적 오류 상세 정보나 Stack Trace는 화면에 그대로 표시하지 않는다.

개발자가 확인할 수 있는 수준의 Console Logging은 최소한으로 사용할 수 있다.

---

# 33. Loading 표현

Agent가 실행 중임을 사용자가 알 수 있도록 최소한의 Loading 상태를 제공한다.

예:

```text id="9wgy0t"
응답 생성 중...
```

또는 `status` Event가 존재하면 해당 상태를 우선 표시한다.

외부 Loading Spinner Package는 사용하지 않는다.

---

# 34. Scroll 처리

새로운 Message나 Streaming Text가 추가되면 대화의 최신 부분을 확인하기 쉽도록 기본적인 Auto Scroll을 구현한다.

외부 Scroll Library는 사용하지 않는다.

React `ref`와 Browser API를 사용한다.

---

# 35. Tests / 검증

현재 프로젝트에 Frontend Test Framework가 이미 존재한다면 최소한의 Component/API Test를 추가할 수 있다.

Test Framework가 없다면 신규 Package를 추가하지 않는다.

대신 다음 검증을 우선한다.

```text id="n3tf7v"
npm run build
npm run lint
```

가능한 환경에서 수행한다.

---

# 36. 외부 Network 점검

구현 완료 후 코드 전체에서 다음 내용을 확인한다.

```text id="m39429"
http://
https://
fetch(
google
vercel
analytics
telemetry
cdn
```

FastAPI Backend 주소 외의 외부 Network 의존이 없는지 확인한다.

---

# 37. 구현 완료 후 확인

다음을 확인한다.

```text id="wt0rvn"
- Next.js 실행 가능
- Chat UI 렌더링
- 사용자 질문 입력 가능
- /api/chat 호출 가능
- SSE Streaming 수신 가능
- text Event 표시
- status Event 표시
- tool_result Event 표시
- error Event 처리
- done Event 처리
- conversation_id 전달 가능
- Streaming 중 Loading 상태 표시
- Abort 가능한 구조
- Backend AgentEvent와 Frontend Type 일치
- shadcn 사용하지 않음
- 외부 Font 사용하지 않음
- 불필요한 신규 Dependency 없음
```

---

# 38. 이번 작업 완료 기준

```text id="0nweno"
[ ] frontend 기본 폴더 구조 생성
[ ] Next.js App Router 구조 적용
[ ] Tailwind 기본 스타일 적용
[ ] ChatWindow 생성
[ ] MessageBubble 생성
[ ] MessageInput 생성
[ ] StatusCard 생성
[ ] ToolResultCard 생성
[ ] AgentEvent Type 생성
[ ] Backend /api/chat 연결 구조 생성
[ ] conversation_id 전달 구조 생성
[ ] SSE Streaming 처리 가능
[ ] text/status/tool_call/tool_result/error/done 처리
[ ] Loading 상태 처리
[ ] Error 처리
[ ] Auto Scroll 기본 처리
[ ] AbortController 사용 가능한 구조
[ ] Vercel AI SDK 존재 여부 확인
[ ] AI SDK 존재 시 활용 가능
[ ] AI SDK 없어도 동작 가능한 구조
[ ] shadcn 사용 안 함
[ ] 외부 Network Dependency 없음
[ ] 실제 고급 업무 UI는 아직 구현하지 않음
```

---

# 핵심 아키텍처

최종적으로 다음 흐름이 명확하게 드러나도록 구현한다.

```text id="ytw08p"
                    User
                     │
                     ▼
                MessageInput
                     │
                     ▼
                 ChatWindow
                     │
                     ▼
              Chat API / Transport
                     │
                POST /api/chat
                     │
                     ▼
                   FastAPI
                     │
                     ▼
             Claude Agent SDK
                     │
                     ▼
                 AgentEvent
                     │
                     │ SSE
                     ▼
                 Frontend
                     │
          ┌──────────┼───────────┐
          ▼          ▼           ▼
        Text       Status     Tool Result
          │          │           │
          └──────────┼───────────┘
                     ▼
                  Chat UI
```

가장 중요한 원칙은 다음이다.

```text id="ojp3c1"
Frontend
   ↓
AgentEvent
   ↓
Backend API
   ↓
Claude Agent SDK
```

Frontend는 Claude Agent SDK 내부 구현에 직접 의존하지 않는다.

Vercel AI SDK의 존재 여부 역시 Frontend 전체 구조에 영향을 주지 않도록 한다.

```text id="aw2x10"
AI SDK 있음
 → AI SDK 활용

AI SDK 없음
 → Browser 기본 Streaming 사용
```

어떤 방식이든 Backend와의 `AgentEvent` Contract는 동일하게 유지한다.

향후 SQL 결과 Table, RAG 문서 목록, Simulation KPI, Chart, Scenario Comparison 등의 업무 UI가 추가되더라도 현재 Chat Component 구조를 기반으로 자연스럽게 확장할 수 있도록 구현한다.