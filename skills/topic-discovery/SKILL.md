# topic-discovery

- 유형: AI + search
- 진입점: `topic_discovery.py` 의 `run(request, ...)` (공통 JSON 봉투, [DATA_SCHEMA](../../docs/DATA_SCHEMA.md))
- 책임: 편집 맥락에서 한국어 블로그 주제 후보 5~10개를 검색 근거와 함께 제안한다. 선택은 사람이 한다.

## 입력 (`input`)
`editorial_context`, `active_content_types`, `requested_content_types`?, `candidate_count`(5~10, 기본 5), `discovery_criteria`?, `excluded_topics`?, `blocked_terms`?, `locale`?(기본 `ko-KR`, 현재 `ko-KR`만 허용·그 외 `INVALID_INPUT`)

## 출력 (`output`)
`candidates[]`(유형·제목·대표 키워드 1·연관 키워드 3~5·검색 의도·추천 이유·freshness·`requires_firsthand_experience`(experience·review는 true)·`sources[]`), `warnings[]`

## 규칙과 오류
refs: `discovery_run_id`. 근거 URL은 검색 결과 번호로만 연결(모델이 URL을 만들 수 없음). ID·점수 없음. 검색 2회 이내. 5개 미만이면 `INSUFFICIENT_EVIDENCE`, 요청 수 미달이면 `REQUESTED_COUNT_NOT_MET` 경고. 식별정보는 검색 전에 `INVALID_INPUT`.

공통: 공급자/모델은 주입(`llm(role, system, prompt)`, `search(query, max_results)`)이며 코드에 하드코딩하지 않는다. 역할(role)은 `config/model-config.json`의 `tasks.<작업>.model`에서 읽는다. 공급자 예외는 `API_TRANSIENT`/`API_RATE_LIMITED`/`AUTH_OR_PERMISSION`으로 변환된다. refs의 `content_id`·`topic_id` 형식이 틀리면 AI 호출 전에 `INVALID_INPUT`. 산출물 `artifact`에는 `checksum`(sha256)이 붙는다. 응답 봉투의 `usage`에 AI·검색 호출 수, 어댑터가 보고한 토큰 수, `input_hash`가 담긴다(Execution Logs 기록용). JSON 수정 재시도는 최대 2회. 테스트: `tests/unit`.