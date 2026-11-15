# content-planning

- 유형: AI
- 진입점: `content_planning.py` 의 `run(request, ...)` (공통 JSON 봉투, [DATA_SCHEMA](../../docs/DATA_SCHEMA.md))
- 책임: 주제와 조사 자료로 방향·목차·핵심 메시지를 작성한다.

## 입력 (`input`)
`topic{title,content_type,...}`, `research_sources[]`, `version_no`?, `revision_feedback`?

## 출력 (`output`)
`plan{working_title,direction,key_message,outline[],interview_focus[],comparison_criteria[]}`, `artifact`(plan md)

## 규칙과 오류
refs: `content_id`, `topic_id`. 목차는 실제 research_id만 참조. experience/review는 경험 질문 주제 2개 이상, compare는 비교 기준 3개 이상, finance는 유의사항 섹션 자동 추가.

공통: 공급자/모델은 주입(`llm(role, system, prompt)`, `search(query, max_results)`)이며 코드에 하드코딩하지 않는다. 역할(role)은 `config/model-config.json`의 `tasks.<작업>.model`에서 읽는다. 공급자 예외는 `API_TRANSIENT`/`API_RATE_LIMITED`/`AUTH_OR_PERMISSION`으로 변환된다. refs의 `content_id`·`topic_id` 형식이 틀리면 AI 호출 전에 `INVALID_INPUT`. 산출물 `artifact`에는 `checksum`(sha256)이 붙는다. 응답 봉투의 `usage`에 AI·검색 호출 수, 어댑터가 보고한 토큰 수, `input_hash`가 담긴다(Execution Logs 기록용). JSON 수정 재시도는 최대 2회. 테스트: `tests/unit`.