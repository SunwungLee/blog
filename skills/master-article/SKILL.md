# master-article

- 유형: AI + Script 검사
- 진입점: `master_article.py` 의 `run(request, ...)` (공통 JSON 봉투, [DATA_SCHEMA](../../docs/DATA_SCHEMA.md))
- 책임: 승인된 기획·근거·사용자 답변으로 Master Article을 작성한다.

## 입력 (`input`)
`content_type`, `plan`, `research_sources[]`, `answers[]`, `writing_style`?, `sponsored`?, `revision_feedback`?, `version_no`?, `blocked_terms`?, `information_as_of`?(YYYY-MM-DD)

## 출력 (`output`)
`title`, `used_research_ids[]`, `warnings[]`(`PII_REDACTED`, `DONT_KNOW_OMITTED`, `MODEL_WARNING`), `artifact`(master md, `checksum`)

## 규칙과 오류
refs: `content_id`. 최소 분량(`config/quality-rules.json`의 `min_body_chars`, 임시값)·목차·근거 ID·식별정보·금융 금지 표현·AI 상투 표현·미제공 경험 단정을 검사하고 최초 이후 최대 2회만 재작성, 초과 시 `QUALITY_BELOW_THRESHOLD`. experience/review는 답변 없으면 `INSUFFICIENT_EVIDENCE`. 답변의 식별정보·`blocked_terms`는 프롬프트에 넣기 전에 가린다. finance 고지문(정확한 문장)·정보 기준일(`information_as_of` 또는 인용 출처의 최신 확인일), 광고 고지(`sponsored=true`), 참고 자료 목록은 스크립트가 보장.

공통: 공급자/모델은 주입(`llm(role, system, prompt)`, `search(query, max_results)`)이며 코드에 하드코딩하지 않는다. 역할(role)은 `config/model-config.json`의 `tasks.<작업>.model`에서 읽는다. 공급자 예외는 `API_TRANSIENT`/`API_RATE_LIMITED`/`AUTH_OR_PERMISSION`으로 변환된다. refs의 `content_id`·`topic_id` 형식이 틀리면 AI 호출 전에 `INVALID_INPUT`. 산출물 `artifact`에는 `checksum`(sha256)이 붙는다. 응답 봉투의 `usage`에 AI·검색 호출 수, 어댑터가 보고한 토큰 수, `input_hash`가 담긴다(Execution Logs 기록용). JSON 수정 재시도는 최대 2회. 테스트: `tests/unit`.