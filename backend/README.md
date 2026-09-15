# Production Planning Agent Backend

FastAPI와 Claude Agent SDK를 사용해 채팅 이벤트를 SSE로 전달하고, 지식·SQL·
시뮬레이션·결과 저장·시각화 tool을 제공한다.

## 설치와 실행

```bash
conda env create -f environment.yml
conda activate production-planning
pip install -r requirements-dev.txt
cp .env.example .env
python -m scripts.build_smt2020_db

export SERVICE_MODE=mock
PLANNING_AGENT_FAKE=1 uvicorn main:app --reload --port 8000
curl localhost:8000/health
```

실제 Claude Agent SDK 경로는 `PLANNING_AGENT_FAKE`를 끄고 `.env`에 provider와
CLI 설정을 구성한다. `services/real`은 폐쇄망에서 사내 서비스로 교체하는
구현 경계다.

Mock SQL과 simulation 입력 검증은 `datasets/SMT2020_HVLM`,
`datasets/SMT2020_LVHM`을 변환한 `datasets/smt2020.db`를 함께 사용한다.
두 benchmark의 ID가 겹치므로 SQL JOIN에는 `dataset`을 포함해야 한다.

## 검증

```bash
python -m pytest -q
python -m pytest -m e2e  # 실제 CLI/provider 인증 필요
```

## 참고

- [Backend 작업 지침](AGENTS.md)
- [폐쇄망 배포 및 실서비스 이식](docs/CLOSED_NETWORK_SETUP.md)
- [도메인 지식·테이블·CTE 관리](docs/domain-knowledge-management.md)
- [Backend 실행 계획](plan/)
- [전체 기능 계획](../plan/)
