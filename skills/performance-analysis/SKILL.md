# performance-analysis

- 유형: Script + AI(선택)
- 진입점: `performance_analysis.py` 의 `run(request, ...)` (공통 JSON 봉투, [DATA_SCHEMA](../../docs/DATA_SCHEMA.md))
- 책임: 수집된 지표를 결정적으로 집계하고 개선 제안을 만든다.

## 입력 (`input`)
`metrics[]`(platform, metric_name, metric_value, measured_at: ISO 8601), `publishing[]`?(publishing_id, platform, human_published_at)

## 출력 (`output`)
`summary[]`(발행 연결 시 `publishing_id`, `days_since_publish` 포함), `suggestions[]`, `publishing[]`(분석에 쓴 발행 기록), `warnings[]`(`UNKNOWN_METRICS`, `PUBLISHING_REFS_MISSING`, `MEASURED_BEFORE_PUBLISH`, `METRICS_WITHOUT_PUBLISHING`, `NO_METRICS_FOR_PLATFORM`)

## 규칙과 오류
refs: `content_id`. 시계열은 measured_at을 시각으로 해석해 정렬(형식 오류는 `INVALID_INPUT`). 집계·변화율·규칙 기반 제안은 AI 없이 동작하고, 좋아요·댓글이 수집되지 않았으면 참여율을 0으로 보지 않는다. llm이 있으면 가설 형태의 제안을 추가. Publishing 연결(확정, Phase 0 20.13): Workflow가 해당 콘텐츠의 Publishing 행을 넘긴다. `human_published_at`이 있는 행만 쓰고 플랫폼별 최신 발행을 기준으로 한다. 발행 전 측정값은 제외하고, 남는 값이 없으면 `INVALID_INPUT`. 발행 후 `early_period_days`(7일) 안의 조회수 감소는 초기 하락으로 보고 감소 제안을 내지 않는다. `publishing`을 생략하면 지표만 분석하고 `PUBLISHING_REFS_MISSING` 경고를 낸다.

공통: 공급자/모델은 주입(`llm(role, system, prompt)`, `search(query, max_results)`)이며 코드에 하드코딩하지 않는다. 역할(role)은 `config/model-config.json`의 `tasks.<작업>.model`에서 읽는다. 공급자 예외는 `API_TRANSIENT`/`API_RATE_LIMITED`/`AUTH_OR_PERMISSION`으로 변환된다. refs의 `content_id`·`topic_id` 형식이 틀리면 AI 호출 전에 `INVALID_INPUT`. 산출물 `artifact`에는 `checksum`(sha256)이 붙는다. 응답 봉투의 `usage`에 AI·검색 호출 수, 어댑터가 보고한 토큰 수, `input_hash`가 담긴다(Execution Logs 기록용). JSON 수정 재시도는 최대 2회. 테스트: `tests/unit`.