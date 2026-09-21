# Backend 참고 문서 지침

- 이 폴더에는 폐쇄망 설치·이식·운영과 도메인 지식·데이터 관리처럼 개발 중
  반복해서 참고하는 문서를 둔다.
- 구현 일정, Task와 진행 체크리스트는 `plan`에 둔다.
- 실제 사내 URL, 계정, 토큰, 비밀번호와 반입이 금지된 데이터 예시는 기록하지 않는다.
- 테이블·KPI·CTE 설명은 코드의 `knowledge/` YAML을 복제하지 않고 작성·검토
  절차와 필드 의미를 설명한다. 실제 값이 다르면 YAML을 기준으로 한다.
- table·recipe 문서에서 `query_rules`는 조회 기본값, `aggregation_rules`는
  집계 의미, `visualization_hints`는 표현 권고로 구분한다. `sample_queries`는
  `question`, `sql`만 문서화하고 변하는 결과 값은 기록하지 않는다.
- 확인되지 않은 업무 지식은 `draft`, 담당자 검토를 마친 지식은 `verified`로
  구분하고 근거·담당자·갱신일을 기록한다.
- 문서 이동이나 제목 변경 시 README, 계획, 코드 주석의 상대 링크를 함께 갱신한다.
- 실행 명령을 적을 때 Git에 포함된 파일과 별도 반입하는 로컬 dataset·script를
  명확히 구분한다.
