"""PKT 목표수량 swap 산출 mock.

PNS PNT-FP API의 PktTarget 엔드포인트(GET /pkt-target-swap-results/all|swapped,
by plan_prod_ids)가 반환하는 `PktTargetListResponse` 모양을 결정적 합성 데이터로
재현한다. 실제 스냅샷 데이터를 다루지 않으므로 `scripts/generate_mock_database.py`의
SEG_A/SEG_B SQLite와는 별개로, 고정 seed 기반 순수 Python 생성기로 둔다.

SITE→GBM 2단계 swap 우선순위의 정확한 업무 규칙은 폐쇄망 검증 전까지 확인되지
않았다 — 여기서는 우선순위 순서대로 잉여를 부족에 채우는 근사 알고리즘만 재현하며,
수치의 업무적 정확성은 보장하지 않는다.
"""

from __future__ import annotations

import random

PKT_SWAP_SIMULATION_TYPE = "PKT_목표수량_스왑산출"

_SEED = 20260923
_PRODUCT_COUNT = 12
_SITES = ["SITE_A", "SITE_B", "SITE_C"]
_GRADES = ["A", "B", "C"]
_CUSTOMERS = ["CUST_01", "CUST_02", "CUST_03"]
_GBN_CODES = ["SITE", "GBM"]


def _generate_base_rows(rng: random.Random) -> list[dict]:
    """제품(planProductId)·site·grade·customer·swap 우선순위별 planQty/poutQty를
    합성한다. targetQty는 아직 계산하지 않은 원본 행이다."""

    rows: list[dict] = []
    for i in range(_PRODUCT_COUNT):
        plan_product_id = f"PROD_{i + 1:04d}"
        # 같은 제품을 2~3개 site로 나눠 swap이 발생할 여지를 만든다.
        site_count = rng.choice([2, 3])
        sites = rng.sample(_SITES, site_count)
        for site in sites:
            plan_qty = float(rng.randint(500, 5000))
            # 실적이 계획을 넘치거나 못 미치는 케이스를 고르게 섞는다.
            pout_ratio = rng.uniform(0.6, 1.4)
            pout_qty = round(plan_qty * pout_ratio, 1)
            rows.append(
                {
                    "planProductId": plan_product_id,
                    "planYm": "202609",
                    "planVersion": "V1",
                    "osCode": "OS1",
                    "fabId": "FAB1",
                    "site": site,
                    "grade": rng.choice(_GRADES),
                    "customer": rng.choice(_CUSTOMERS),
                    "planQty": plan_qty,
                    "poutQty": pout_qty,
                    "gbnPriority": rng.randint(1, len(_SITES)),
                    "gbnCd": rng.choice(_GBN_CODES),
                }
            )
    return rows


def _apply_swap(rows: list[dict]) -> list[dict]:
    """targetQty = planQty - poutQty를 계산한 뒤, 같은 제품 내에서 우선순위
    순으로 잉여(targetQty>0)를 부족(targetQty<0)에 채워 GIVE/RECEIVE
    swapReason을 채운다."""

    by_product: dict[str, list[dict]] = {}
    for row in rows:
        row = dict(row)
        row["targetQty"] = round(row["planQty"] - row["poutQty"], 1)
        row["swapReason"] = None
        by_product.setdefault(row["planProductId"], []).append(row)

    swap_seq = 0
    for group in by_product.values():
        group.sort(key=lambda r: r["gbnPriority"])
        surplus = [r for r in group if r["targetQty"] < 0]  # 실적 초과 → 양보 가능
        deficit = [r for r in group if r["targetQty"] > 0]  # 실적 부족 → 충전 필요

        for give_row in surplus:
            available = -give_row["targetQty"]
            for receive_row in deficit:
                if available <= 0:
                    break
                need = receive_row["targetQty"]
                if need <= 0:
                    continue
                swap_qty = round(min(available, need), 1)
                if swap_qty <= 0:
                    continue
                swap_seq += 1
                swap_id = f"SWAP_{swap_seq:04d}"
                give_row["targetQty"] += swap_qty
                receive_row["targetQty"] -= swap_qty
                give_row["swapReason"] = {
                    "swapId": swap_id,
                    "direction": "GIVE",
                    "prodGrpNm": give_row["planProductId"],
                    "gbnCd": give_row["gbnCd"],
                    "frParaVal": give_row["site"],
                    "toParaVal": receive_row["site"],
                    "swapQty": swap_qty,
                    "counterPlanProdId": receive_row["planProductId"],
                    "counterSite": receive_row["site"],
                    "counterGrade": receive_row["grade"],
                    "counterCsCode": receive_row["customer"],
                }
                receive_row["swapReason"] = {
                    "swapId": swap_id,
                    "direction": "RECEIVE",
                    "prodGrpNm": receive_row["planProductId"],
                    "gbnCd": receive_row["gbnCd"],
                    "frParaVal": give_row["site"],
                    "toParaVal": receive_row["site"],
                    "swapQty": swap_qty,
                    "counterPlanProdId": give_row["planProductId"],
                    "counterSite": give_row["site"],
                    "counterGrade": give_row["grade"],
                    "counterCsCode": give_row["customer"],
                }
                available -= swap_qty

    rows_out = [row for group in by_product.values() for row in group]
    for row in rows_out:
        row["targetQty"] = round(row["targetQty"], 1)
    return rows_out


def _build_metadata(rows: list[dict]) -> dict:
    total_target = round(sum(r["targetQty"] for r in rows), 1)
    total_plan_qty = round(sum(r["planQty"] for r in rows), 1)
    return {
        "itemCount": len(rows),
        "swapCount": sum(1 for r in rows if r["swapReason"] is not None),
        "totalTarget": total_target,
        "totalPlanQty": total_plan_qty,
        "targetToPlanRatio": round(total_target / total_plan_qty, 4) if total_plan_qty else 0.0,
    }


def generate_pkt_swap_response(
    *, view: str, plan_prod_ids: list[str] | None = None
) -> dict:
    """view별로 필터링한 `{"metadata": {...}, "items": [...]}`를 반환한다
    (PktTargetListResponse와 같은 모양). 같은 view·plan_prod_ids 조합으로
    반복 호출해도 seed가 고정되어 있어 항상 같은 결과를 돌려준다."""

    rng = random.Random(_SEED)
    rows = _apply_swap(_generate_base_rows(rng))

    if view == "by_ids":
        ids = set(plan_prod_ids or [])
        rows = [r for r in rows if r["planProductId"] in ids]
    elif view == "swapped":
        rows = [r for r in rows if r["swapReason"] is not None]
    # view == "all"은 필터 없음

    return {"metadata": _build_metadata(rows), "items": rows}
