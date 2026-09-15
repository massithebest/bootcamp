# SMT2020 SQLite 및 Mock 전환 계획

**상태: 완료. 마지막 갱신: 2026-09-15.**

## 목표

`backend/datasets/SMT2020_HVLM`과 `SMT2020_LVHM`의 공개 FAB benchmark를
하나의 로컬 SQLite DB로 변환하고, 자연어 SQL과 simulation tool의 mock 경로가
같은 DB를 사용하게 한다. 기존 합성 FGS/MP 데이터와 생성기는 제거한다.

이번 단계의 simulation은 실제 이산사건 시뮬레이션 결과를 계산하지 않는다.
SMT2020 입력 테이블과 핵심 관계가 정상인지 확인하는 결정적 mock으로 tool·SSE·UI
연동을 검증한다.

## 실제 데이터 확인 결과

- 두 폴더 모두 tab 구분 텍스트이며 `part`, `order`, `WIP`, `tool`, `setup`,
  `setupgrp`, `downcal`, `pmcal`, `attach`, `fromto`와 하나 이상의
  `route_*.txt`를 포함한다.
- HVLM에는 route 2개, LVHM에는 route 10개가 있다. `part_3`, `r_3`처럼 두
  데이터셋 사이에 식별자가 겹치므로 데이터셋 구분 없는 병합 JOIN은 허용하지 않는다.
- 모든 route 파일의 헤더는 동일하다. `route_*.txt`는 `route_step` 하나로 합친다.
- HVLM `WIP.txt` 첫 데이터 행은 마지막 `HOTLOT`, `TRACE` 필드가 생략되어 있다.
  이 경우에만 누락된 뒤쪽 필드를 `NULL`로 채워 행을 보존할 수 있다.
- `START`, `DUE`의 비어 있지 않은 값은 모두 `%m/%d/%y %H:%M:%S`로 파싱된다.

## 범위와 비범위

### 범위

- 원본 TSV를 재현 가능하게 변환하는 표준 라이브러리 기반 스크립트
- `backend/datasets/smt2020.db` 생성과 반복 실행 시 안전한 원자적 교체
- 두 데이터셋을 구분하는 `dataset` 컬럼과 조회용 인덱스
- SMT2020 catalog·KPI·glossary·simulation 지식
- mock SQL과 mock simulation의 단일 DB 사용
- Fake Runner와 프론트 더미 콘텐츠의 SMT2020 전환
- 변환, row count, schema, index, JOIN, service와 UI 관통 검증

### 비범위

- 실제 FAB simulator, 이벤트 스케줄링과 completion/throughput 예측
- 병목, 가동률, 납기 달성률을 실제 simulation 결과처럼 산출하는 휴리스틱
- 운영 DB 호환 View, 과도한 정규화와 외래키 중심 재설계
- 데이터셋 선택을 위한 별도 API나 프론트 UI
- `services/real`의 사내 DB·simulation provider 구현

## 공유 SQLite 계약

출력 DB는 하나이며 모든 테이블의 첫 컬럼은 `dataset TEXT NOT NULL`이다. 값은
원본 폴더 접미사에서 얻은 `HVLM` 또는 `LVHM`이다. 같은 데이터셋 안의 관계는
항상 `dataset`과 원본 업무 키를 함께 사용한다.

| 원본 | SQLite 테이블 | 주요 관계 키 |
| --- | --- | --- |
| `part.txt` | `part` | `dataset, part`, `dataset, route` |
| `route_*.txt` | `route_step` | `dataset, route, step`, `dataset, stnfam` |
| `tool.txt.1l` | `tool` | `dataset, stnfam` |
| `order.txt` | `orders` | `dataset, part`, `dataset, order_id` |
| `WIP.txt` | `wip` | `dataset, part`, `dataset, part, curstep` |
| `setup.txt` | `setup` | 원본 구조 유지 |
| `setupgrp.txt` | `setup_group` | 원본 구조 유지 |
| `downcal.txt` | `down_calendar` | 원본 구조 유지 |
| `pmcal.txt` | `pm_calendar` | 원본 구조 유지 |
| `attach.txt` | `calendar_attach` | `dataset, calname`, `dataset, restype, resname` |
| `fromto.txt` | `transport` | 원본 구조 유지 |

컬럼명은 원본 헤더를 소문자화하고 CamelCase 경계에 `_`를 넣는다. 의미가
불명확한 약어는 임의로 풀지 않는다. SQL 사용이 어려운 이름만 아래처럼 고정한다.

| 원본 | SQLite 컬럼 |
| --- | --- |
| `ORDER` | `order_id` |
| `DESC` | `description` |
| `WHEN` | `when_value` |
| `IGNORE` | `ignore_value` |
| `RPT#` | `rpt_no` |

- 빈 필드는 `NULL`이며 setup/setup group의 빈 선행 값도 carry-forward하지 않는다.
- 숫자 후보는 테이블 단위 전체 비어 있지 않은 값이 변환될 때만
  `INTEGER`/`REAL`로 적재한다. 하나라도 불확실하면 해당 컬럼 전체를 원문
  `TEXT`로 보존한다.
- 날짜 후보도 전체 값이 파싱될 때만 ISO `YYYY-MM-DD HH:MM:SS` `TEXT`로
  바꾼다. 실패하면 원문 `TEXT`를 보존한다.
- 원본 행보다 필드가 많거나, 마지막 필드 생략으로 설명할 수 없는 구조 오류는
  파일명과 행 번호를 포함해 실패시킨다.

## Mock 계약

- 설정 키 `SAMPLE_DB_PATH`를 제거하고 `SMT2020_DB_PATH`를 추가한다. 기본값은
  `backend/datasets/smt2020.db`다.
- `execute_sql`의 함수 시그니처, 읽기 전용 guard, `MAX_ROWS`, Result Store와
  반환 payload는 유지한다. 허용 테이블은 SMT2020 catalog에서 가져온다.
- `list_simulation`은 `SMT2020_입력검증`만 노출한다.
- `run_simulation("SMT2020_입력검증", {"dataset": "LVHM"})`처럼 호출하며
  dataset 입력은 대소문자와 무관하게 받아 대문자로 정규화한다.
- simulation 결과는 기존 simulation result 계약을 사용한다.
  - `kpis`: part, route step, tool family, 초기 WIP lot 수
  - `table`: 11개 테이블별 row count
  - `results`: part→route, route_step→tool, wip→part, orders→part,
    wip curstep→route step의 source/matched/unmatched 건수
  - `summary`: 실제 DES 결과가 아닌 입력 정합성 mock임을 명시
- `AgentEvent`, tool 이름, Result Store, visualization API와 프론트
  `ToolResult` 타입은 바꾸지 않는다.

## 파트별 할당과 의존 관계

- Backend는 변환기, DB schema/index, 기존 합성 시드 제거, catalog와 mock service,
  Fake Runner 및 테스트를 담당한다. 세부 내용은
  [백엔드 실행 계획](../backend/plan/260915-smt2020-mock-data-plan.md)을 따른다.
- Frontend는 SMT2020 기반 예시·더미 대화 교체와 기존 database/simulation/chart
  렌더링의 관통 검증을 담당한다. 세부 내용은
  [프론트엔드 실행 계획](../frontend/plan/260915-smt2020-mock-data-plan.md)을 따른다.
- 프론트 관통 검증은 백엔드 변환, catalog, Fake Runner와 simulation payload가
  완료된 뒤 수행한다.
- 기존 완료 계획은 실행 당시 이력으로 보존한다. 이 계획이 합성 FGS/MP mock을
  대체한다는 사실만 `Todo.md`와 현재 운영 문서에 반영한다.

## 전체 인수 조건

- 변환 스크립트를 연속 실행해도 정상 DB가 안전하게 교체되고, 실패한 재생성이
  이전 정상 DB를 훼손하지 않는다.
- 생성된 테이블과 row count가 아래 실제 원본 건수와 일치한다.

| 테이블 | HVLM | LVHM | 합계 |
| --- | ---: | ---: | ---: |
| `part` | 2 | 10 | 12 |
| `route_step` | 926 | 4,013 | 4,939 |
| `tool` | 106 | 106 | 212 |
| `orders` | 5 | 21 | 26 |
| `wip` | 2,255 | 2,156 | 4,411 |
| `setup` | 13 | 13 | 26 |
| `setup_group` | 9 | 9 | 18 |
| `down_calendar` | 11 | 11 | 22 |
| `pm_calendar` | 292 | 292 | 584 |
| `calendar_attach` | 303 | 303 | 606 |
| `transport` | 1 | 1 | 2 |

- `part → route_step`, `route_step → tool`, `part → wip`, `part → orders`,
  `wip → part → route_step`의 dataset-safe JOIN이 실행되고 unmatched가 0이다.
- 제품별 WIP와 제품별 공정 Step 수 예제 SQL이 정상 실행된다.
- mock SQL과 두 데이터셋의 입력 검증 simulation이 같은 DB를 조회한다.
- Fake Runner에서 catalog→SQL→simulation→bar chart→답변 흐름이 오류 없이 끝난다.
- 백엔드 전체 테스트, 프론트 lint/build와 문서 링크·diff 검증을 통과한다.

## 실행 결과

- `backend/scripts/build_smt2020_db.py`로 HVLM/LVHM 원본을 하나의
  `backend/datasets/smt2020.db`로 변환했다. 스크립트를 연속 두 번 실행해 동일한
  11개 테이블과 계획 기준 row count가 생성됨을 확인했다.
- 다섯 핵심 관계의 dataset-safe JOIN은 HVLM/LVHM 모두 unmatched 0건이었고,
  제품별 WIP와 제품별 공정 Step 수 조회는 각각 12개 그룹을 반환했다.
- 기존 합성 SQLite와 seed를 제거하고 catalog, `initial_wip` KPI,
  `SMT2020_입력검증`, Fake Runner와 프론트 예시를 같은 DB 기준으로 교체했다.
- `python -m pytest -q`는 189건 통과(실 provider E2E 5건 deselected), 프론트
  lint/build는 오류 없이 통과했다. lint의 기존 Fast Refresh 경고 4건과 Vite의
  번들 크기 경고는 이 작업의 실패 조건이 아니다.
- 격리한 Fake backend/frontend를 브라우저로 관통해 SQL 표, 입력 관계 표,
  bar 차트와 최종 답변을 확인했다. 콘솔 오류와 error overlay는 없었고 400px에서
  페이지 수평 overflow도 발생하지 않았다.
