# seo-optimization

- 유형: Script 우선 + AI
- 진입점: `seo_optimization.py` 의 `run(request, ...)` (공통 JSON 봉투, [DATA_SCHEMA](../../docs/DATA_SCHEMA.md))
- 책임: 기계적 SEO 검사를 먼저 하고, 필요할 때만 AI로 제목·메타·소제목·표현을 다듬는다.

## 입력 (`input`)
`article_markdown`, `title`, `primary_keyword`, `related_keywords[]`, `search_intent`?, `meta_description`?, `content_type`?, `blocked_terms`?, `seo_config`?, `version_no`?

## 출력 (`output`)
`optimized`, `requires_refactcheck`, `title`, `meta_description`, `changes[]`, `before`, `after`, `warnings[]`(`SEO_NOT_FULLY_PASSED`, `REFACTCHECK_REQUIRED`), `artifact`(final md, `checksum`)

## 규칙과 오류
refs: `content_id`. 이미 통과하면 AI 호출 없음. 제목·메타 검사만 실패하면 제목·메타만 다시 쓰고 본문은 그대로 둔다(토큰 절감). 본문 재작성 시 숫자 추가·삭제, 링크 추가·삭제, 고지문 삭제, 제목·메타의 새 숫자, 본문 분량 10% 초과 증가(`seo_max_body_growth`), 금융 금지·상투 표현·식별정보가 있으면 재작성(최대 2회) 후 `QUALITY_BELOW_THRESHOLD`. 본문이 바뀌면 `requires_refactcheck=true`이므로 Workflow는 승인 전에 fact-checking을 다시 실행한다. 최소 분량 기준은 master-article과 같은 `min_body_chars`.

공통: 공급자/모델은 주입(`llm(role, system, prompt)`, `search(query, max_results)`)이며 코드에 하드코딩하지 않는다. 역할(role)은 `config/model-config.json`의 `tasks.<작업>.model`에서 읽는다. 공급자 예외는 `API_TRANSIENT`/`API_RATE_LIMITED`/`AUTH_OR_PERMISSION`으로 변환된다. refs의 `content_id`·`topic_id` 형식이 틀리면 AI 호출 전에 `INVALID_INPUT`. 산출물 `artifact`에는 `checksum`(sha256)이 붙는다. 응답 봉투의 `usage`에 AI·검색 호출 수, 어댑터가 보고한 토큰 수, `input_hash`가 담긴다(Execution Logs 기록용). JSON 수정 재시도는 최대 2회. 테스트: `tests/unit`.