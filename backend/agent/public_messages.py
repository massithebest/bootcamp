"""실행부 공통 공개 오류 문구.

`error` 이벤트로 사용자에게 보이는 문구다. 내부 예외·provider 정보는 넣지 않는다.
"""

LLM_RESPONSE_TIMEOUT_MESSAGE = (
    "LLM API 서버 응답이 지연되고 있습니다. 잠시 후에 다시 시도해 주세요."
)
LLM_API_FAILURE_MESSAGE = "LLM API 서버 호출에 실패했습니다. 잠시 후에 다시 시도해 주세요."
LLM_TOKEN_CAP_MESSAGE = "LLM API 월간 사용 한도에 도달해 답변할 수 없습니다. 관리자에게 문의해 주세요."
INCOMPLETE_RESPONSE_MESSAGE = "Agent 응답이 완료되기 전에 종료되었습니다."
MAX_TURNS_MESSAGE = (
    "질문을 처리하는 단계가 너무 많아 응답을 마치지 못했습니다. 질문을 나눠서 다시 요청해 주세요."
)
FORK_FALLBACK_MESSAGE = "이전 응답 지점을 찾을 수 없어 새 대화로 시작합니다."
