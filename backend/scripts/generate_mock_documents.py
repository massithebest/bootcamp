"""일반 생산계획 용어집을 문서 저장소에 등록해 ``search_documents``로 조회되게 한다.

Git 포함 대상이다. 문서 원본은 이 파일 안의 상수(``DOCUMENTS``)에 직접 담겨 있으며
외부 파일을 읽지 않는다. 저장소(``KNOWLEDGE_DB_PATH``)에는 기존 작성 절차
(저장 → 검토 → 활성화)를 그대로 거쳐 등록한다.

backend/ 에서 실행::

    python -m scripts.generate_mock_documents            # 등록·갱신
    python -m scripts.generate_mock_documents --dry-run   # 변경 없이 대상만 출력

여러 번 실행해도 안전하다. 내용이 같으면 건너뛰고, 바뀌었으면 새 버전을 만든다.
"""
from __future__ import annotations

import argparse
import re
import sys

from services.knowledge.documents import DocumentStore, get_document_store

OWNER = "mock-generator"
ACTOR = "mock-generator"
REVIEW_NOTE = "합성 mock 문서 자동 등록"
SOURCE_PREFIX = "mock-docs/"
CATEGORY = "production_planning"
RELATED_HEADING = "관련 용어"

DOCUMENTS: dict[str, str] = {
    "route": """# Route(공정 경로)

## 정의
Route는 하나의 제품(Part)이 완성되기까지 거쳐야 하는 공정 Step의 순서를 정의한
경로다. 각 Step은 특정 설비 Family(Tool)에서 처리된다.

## 주요 특징
- 제품(Part) 마스터가 하나의 Route를 참조한다
- Route는 여러 Step으로 구성되며 Step 번호 순서로 진행된다
- 각 Step은 처리 시간(Ptime)과 설비 Family(Stnfam)를 갖는다
- 같은 Route ID라도 생산 세그먼트(Segment)가 다르면 서로 다른 정의일 수 있다

## 관련 용어
- Step
- Part
- Tool
- Segment

## 예시 질문
- Route란 무엇인가?
- 특정 Part의 Route Step은 몇 개인가?
""",
    "wip": """# WIP(재공)

## 정의
WIP(Work In Process)는 아직 완성되지 않고 공정 중간에 있는 Lot(로트)의 재고를
말한다. 각 WIP는 현재 몇 번째 Step(CurStep)에 있는지를 함께 기록한다.

## 주요 특징
- Lot 단위로 관리되며 Part, 현재 Step, 수량(Pieces)을 함께 기록한다
- CurStep은 해당 Part의 Route에 실제로 존재하는 Step이어야 한다
- 초기 WIP 집계는 생산계획 시뮬레이션의 시작점(초기 조건)으로 쓰인다

## 관련 용어
- Lot
- Route
- Step
- Order

## 예시 질문
- WIP란 무엇인가?
- 세그먼트별 초기 WIP 수량은 얼마인가?
""",
    "setup": """# Setup(교체 시간)

## 정의
Setup은 설비가 한 작업(Setup 상태)에서 다른 작업으로 바뀔 때 필요한 준비·교체
시간이다. 같은 Setup Group에 속한 작업으로 전환할 때는 교체 시간이 줄어들 수 있다.

## 주요 특징
- 이전 Setup(CurSetup)에서 다음 Setup(NewSetup)으로 바뀔 때의 소요 시간을 정의한다
- Setup Group은 서로 교체 시간이 짧은 Setup들을 묶은 그룹이다
- Route Step은 자신이 요구하는 Setup 값을 가질 수 있다

## 관련 용어
- Setup Group
- Route
- Tool

## 예시 질문
- Setup(교체 시간)이란 무엇인가?
- Setup Group은 왜 필요한가?
""",
    "down_calendar": """# Downtime Calendar(비계획 정지)

## 정의
Downtime Calendar는 설비의 비계획적인 고장·정지 패턴을 정의하는 캘린더다.
평균 고장 간격(MTTF)과 평균 수리 시간(MTTR)으로 표현된다.

## 주요 특징
- MTTF(Mean Time To Failure)는 고장까지 걸리는 평균 시간이다
- MTTR(Mean Time To Repair)는 고장 후 복구까지 걸리는 평균 시간이다
- 특정 설비(Resource)에 Calendar Attach로 연결되어 적용된다

## 관련 용어
- PM Calendar
- Calendar Attach
- Tool

## 예시 질문
- Downtime Calendar란 무엇인가?
- MTTF와 MTTR의 차이는 무엇인가?
""",
    "pm_calendar": """# PM Calendar(예방 정비)

## 정의
PM(Preventive Maintenance) Calendar는 정해진 주기로 계획된 정비를 수행하는
일정을 정의하는 캘린더다. 비계획 정지(Downtime)와 달리 미리 예측 가능하다.

## 주요 특징
- MTBPM(Mean Time Between PM)은 정비 간 평균 간격이다
- 정비 소요 시간(MTTR)을 함께 정의한다
- 설비 가동률(가용성) 계산에 영향을 준다

## 관련 용어
- Downtime Calendar
- Calendar Attach
- Tool

## 예시 질문
- PM Calendar란 무엇인가?
- 예방 정비와 비계획 정지의 차이는 무엇인가?
""",
    "transport": """# Transport(운반)

## 정의
Transport는 한 위치(FromLoc)에서 다른 위치(ToLoc)로 Lot을 옮기는 데 걸리는
운반 시간을 정의한다.

## 주요 특징
- 출발지·도착지 조합별로 운반 시간 분포를 정의한다
- 공정 간 이동이 잦은 라인일수록 운반 시간이 전체 리드타임에 미치는 영향이 크다

## 관련 용어
- Route
- Lot

## 예시 질문
- Transport(운반)란 무엇인가?
- 운반 시간은 어떻게 정의되는가?
""",
    "lot": """# Lot(로트)

## 정의
Lot은 생산계획에서 함께 이동·관리되는 제품 묶음의 기본 단위다. 신규 투입되는
Lot은 Order(주문)로, 이미 공정 중인 Lot은 WIP로 관리된다.

## 주요 특징
- Part, 수량(Pieces), 우선순위(Prior)를 함께 갖는다
- 착수 예정일(Start)과 납기(Due)를 가진다
- Hotlot으로 지정되면 다른 Lot보다 우선 처리된다

## 관련 용어
- Order
- WIP
- Part

## 예시 질문
- Lot이란 무엇인가?
- Hotlot은 무엇을 의미하는가?
""",
    "tool_capacity": """# Tool/Station Capacity(설비 능력)

## 정의
Tool(Station Family)은 특정 공정 Step을 처리하는 설비 그룹이다. 설비마다
처리 가능한 수량(Capacity)과 대수(Qty), 처리 시간(Ltime/Ultime)이 다르다.

## 주요 특징
- 같은 Stnfam(설비 Family)에 여러 대의 동일 설비가 있을 수 있다(Stnqty)
- Ltime/Ultime은 각각 하한·상한 처리 시간을 나타낸다
- 설비는 Setup Group을 가져 교체 시간 규칙을 따른다

## 관련 용어
- Route
- Setup
- Setup Group

## 예시 질문
- Tool Capacity란 무엇인가?
- 설비 대수(Stnqty)는 무엇에 영향을 주는가?
""",
    "segment_strategy": """# 생산 세그먼트 전략(고Volume-저Mix vs 저Volume-고Mix)

## 정의
생산계획에서는 제품 종류(Mix)와 생산량(Volume)의 조합에 따라 운영 전략이
달라진다. 소품종 대량생산(고Volume-저Mix)과 다품종 소량생산(저Volume-고Mix)은
서로 다른 설비 배치·Setup 전략이 필요하다.

## 주요 특징
- 고Volume-저Mix는 적은 제품군을 대량으로 생산해 Setup 교체가 적다
- 저Volume-고Mix는 다양한 제품을 소량씩 생산해 Setup 교체가 잦다
- 같은 설비·Route 정의라도 세그먼트에 따라 실제 운영 지표가 달라질 수 있다

## 관련 용어
- Segment
- Setup
- Route

## 예시 질문
- 고Volume-저Mix와 저Volume-고Mix의 차이는 무엇인가?
- 생산 세그먼트는 왜 구분해서 관리하는가?
""",
}


def build_document(slug: str, text: str) -> dict:
    text = text.strip()
    match = re.match(r"#\s+(.+)", text)
    if not match:
        raise ValueError(f"{slug}: 첫 줄이 '# 제목' 이어야 합니다.")
    title = match.group(1).strip()
    tags = [title]
    section = re.search(rf"^##\s+{RELATED_HEADING}\s*\n(.*?)(?=^##\s|\Z)", text, re.S | re.M)
    if section:
        tags += re.findall(r"^-\s+(.+)$", section.group(1), re.M)
    return {
        "title": title, "content": text, "category": CATEGORY,
        "tags": list(dict.fromkeys(t.strip() for t in tags if t.strip()))[:30],
        "owner": OWNER,
        "source": f"{SOURCE_PREFIX}{slug}",
    }


def seed(store: DocumentStore, docs: list[dict]) -> dict[str, int]:
    """문서를 등록한다. source 기준으로 기존 문서를 찾아 변경분만 새 버전으로 만든다."""
    existing = {d["versions"][0]["source"]: d for d in store.list() if d["versions"]}
    counts = {"created": 0, "updated": 0, "skipped": 0}
    for fields in docs:
        current = existing.get(fields["source"])
        if current is not None and not current["archived"]:
            latest = current["versions"][0]
            same = all(latest[k] == fields[k] for k in fields)
            if same and current["active_version"] == latest["version"] and latest["status"] == "verified":
                counts["skipped"] += 1
                continue
            saved = store.save(fields, current["id"], current["revision"])
            counts["updated"] += 1
        else:
            saved = store.save(fields)
            counts["created"] += 1
        version = saved["versions"][0]["version"]
        reviewed = store.transition(saved["id"], "review", saved["revision"],
                                    version=version, actor=ACTOR, note=REVIEW_NOTE)
        store.transition(saved["id"], "activate", reviewed["revision"], version=version, actor=ACTOR)
    return counts


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dry-run", action="store_true", help="저장소를 바꾸지 않고 대상만 출력")
    args = parser.parse_args(argv)
    docs = [build_document(slug, text) for slug, text in DOCUMENTS.items()]
    if args.dry_run:
        for d in docs:
            print(f"{d['source']}  title={d['title']!r}  tags={len(d['tags'])}")
        return 0
    counts = seed(get_document_store(), docs)
    print(f"문서 {len(docs)}건 처리: {counts}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
