# source-research

- 유형: AI + search
- 진입점: `source_research.py` 의 `run(request, ...)` (공통 JSON 봉투, [DATA_SCHEMA](../../docs/DATA_SCHEMA.md))
- 책임: 승인된 주제의 출처 메타데이터와 근거 요약을 수집한다.

## 입력 (`input`)
`topic{title,content_type,primary_keyword?}`, `research_questions[]`, `source_criteria{min_sources,max_sources}`?, `blocked_terms`?, `version_no`?

## 출력 (`output`)
`sources[]`(research_id UUID·URL·발행처·게시일·확인일·source_type·근거 요약·`verification_status=unverified`), `gaps[]`, `warnings[]`, `artifact`(research md)

## 규칙과 오류
refs: `content_id`, `topic_id`. 공식 출처 여부는 도메인으로만 판정. 게시일은 검색 결과 메타데이터만 사용(모델이 말한 날짜는 쓰지 않음). 근거 요약에 검색 결과(제목·스니펫)에 없는 숫자가 있으면 그 출처를 제외하고 `SUMMARY_NUMBER_NOT_IN_SOURCE` 경고. finance는 공식 출처 필수. 출처 부족 시 `INSUFFICIENT_EVIDENCE`.

공통: 공급자/모델은 주입(`llm(role, system, prompt)`, `search(query, max_results)`)이며 코드에 하드코딩하지 않는다. 역할(role)은 `config/model-config.json`의 `tasks.<작업>.model`에서 읽는다. 공급자 예외는 `API_TRANSIENT`/`API_RATE_LIMITED`/`AUTH_OR_PERMISSION`으로 변환된다. refs의 `content_id`·`topic_id` 형식이 틀리면 AI 호출 전에 `INVALID_INPUT`. 산출물 `artifact`에는 `checksum`(sha256)이 붙는다. 응답 봉투의 `usage`에 AI·검색 호출 수, 어댑터가 보고한 토큰 수, `input_hash`가 담긴다(Execution Logs 기록용). JSON 수정 재시도는 최대 2회. 테스트: `tests/unit`.