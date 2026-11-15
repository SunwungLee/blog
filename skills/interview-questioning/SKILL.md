# interview-questioning

- 유형: Script + AI
- 진입점: `interview_questioning.py` 의 `run(request, ...)` (공통 JSON 봉투, [DATA_SCHEMA](../../docs/DATA_SCHEMA.md))
- 책임: 필수 질문 미응답을 막고, 누락·모순에 대해서만 추가 질문 1~3개를 만든다.

## 입력 (`input`)
`content_type`, `templates[]`, `answers[]`, `plan`?, `blocked_terms`?

## 출력 (`output`)
`pending_questions[]`, `missing_required[]`, `can_advance`, `conflicts[]`, `followup_questions[]`, `warnings[]`(`PII_IN_ANSWER`, `GAP_ANALYSIS_SKIPPED`)

## 규칙과 오류
refs: `content_id`. 템플릿은 최신 version·active만. "모름"은 답변으로 인정하며 다시 묻지 않음. 필수 질문이 남아 있으면 AI를 호출하지 않음. 개인정보·`blocked_terms`가 있는 답변은 AI에 보내지 않음. AI 공급자가 없으면 분석을 건너뛰고 `GAP_ANALYSIS_SKIPPED` 경고. 후속 질문 ID는 코드가 만드는 UUID.

공통: 공급자/모델은 주입(`llm(role, system, prompt)`, `search(query, max_results)`)이며 코드에 하드코딩하지 않는다. 역할(role)은 `config/model-config.json`의 `tasks.<작업>.model`에서 읽는다. 공급자 예외는 `API_TRANSIENT`/`API_RATE_LIMITED`/`AUTH_OR_PERMISSION`으로 변환된다. refs의 `content_id`·`topic_id` 형식이 틀리면 AI 호출 전에 `INVALID_INPUT`. 산출물 `artifact`에는 `checksum`(sha256)이 붙는다. 응답 봉투의 `usage`에 AI·검색 호출 수, 어댑터가 보고한 토큰 수, `input_hash`가 담긴다(Execution Logs 기록용). JSON 수정 재시도는 최대 2회. 테스트: `tests/unit`.