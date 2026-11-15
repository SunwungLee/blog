# fact-checking

- 유형: AI + Script 검증
- 진입점: `fact_checking.py` 의 `run(request, ...)` (공통 JSON 봉투, [DATA_SCHEMA](../../docs/DATA_SCHEMA.md))
- 책임: 원고의 주장별로 조사 근거와 대조한다.

## 입력 (`input`)
`article_markdown`, `content_type`, `research_sources[]`, `article_version_id`(필수), `max_unverified_ratio`?

## 출력 (`output`)
`passed`, `reasons[]`, `counts`, `claims[]`(Fact Checks 행 필드: `fact_check_id`, `content_id`, `article_version_id`, `claim_text`, `result`, `research_id`, `note`, `checked_at`, `created_by_run_id`), `unresolved_claims[]`

## 규칙과 오류
refs: `content_id`. 원고에 없는 주장은 버림, 근거 ID가 없거나 수치가 근거 요약에 없으면 확인 불가로 강등, 수치 문장은 누락 시 자동 추가, finance는 `source_type=official` 근거만 인정(유형 미상은 불인정). 모순·근거 없음·미확인 비율 초과(`config/quality-rules.json`, 임시값) 시 `passed=false`. `passed=false`는 성공 응답이며, Workflow가 이를 `QUALITY_BELOW_THRESHOLD`(Phase 0 14.1)로 기록하고 원고 수정 단계로 되돌린다. `result` 값: `supported`/`unsupported`/`contradicted`/`unverifiable`. 현재 검색 재확인은 하지 않고 source-research의 근거 요약만 대조한다.

공통: 공급자/모델은 주입(`llm(role, system, prompt)`, `search(query, max_results)`)이며 코드에 하드코딩하지 않는다. 역할(role)은 `config/model-config.json`의 `tasks.<작업>.model`에서 읽는다. 공급자 예외는 `API_TRANSIENT`/`API_RATE_LIMITED`/`AUTH_OR_PERMISSION`으로 변환된다. refs의 `content_id`·`topic_id` 형식이 틀리면 AI 호출 전에 `INVALID_INPUT`. 산출물 `artifact`에는 `checksum`(sha256)이 붙는다. 응답 봉투의 `usage`에 AI·검색 호출 수, 어댑터가 보고한 토큰 수, `input_hash`가 담긴다(Execution Logs 기록용). JSON 수정 재시도는 최대 2회. 테스트: `tests/unit`.