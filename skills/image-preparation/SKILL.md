# image-preparation

- 유형: AI + Script
- 진입점: `image_preparation.py` 의 `run(request, ...)` (공통 JSON 봉투, [DATA_SCHEMA](../../docs/DATA_SCHEMA.md))
- 책임: 이미지 계획과 권리 메타데이터를 만든다. 권리가 확인되지 않은 이미지는 사용 불가로 표시한다.

## 입력 (`input`)
`article_markdown`, `constraints{max_images(1~15),allowed_source_types,max_width(1~4000)}`?, `assets[]{image_id,source_type,drive_file_id,rights_note,rights_checked_at,width?,height?}`?, `blocked_terms`?

## 출력 (`output`)
`image_plan[]`(status `PLANNED`), `assets[]`(status `RIGHTS_CONFIRMED`/`PENDING_RIGHTS`, `problems[]`, `resize_to`), `usable_image_ids[]`, `unusable_image_ids[]`, `warnings[]`

## 규칙과 오류
refs: `content_id`. 얼굴·식별 요소가 있는 계획은 제외. `image_id`(Images 시트 발급)·`drive_file_id`·권리 메모·확인 시각이 모두 있어야 확정. `image_id`가 없는 자산은 임의 ID를 만들지 않고 `PENDING_RIGHTS`로 둔다.

공통: 공급자/모델은 주입(`llm(role, system, prompt)`, `search(query, max_results)`)이며 코드에 하드코딩하지 않는다. 역할(role)은 `config/model-config.json`의 `tasks.<작업>.model`에서 읽는다. 공급자 예외는 `API_TRANSIENT`/`API_RATE_LIMITED`/`AUTH_OR_PERMISSION`으로 변환된다. refs의 `content_id`·`topic_id` 형식이 틀리면 AI 호출 전에 `INVALID_INPUT`. 산출물 `artifact`에는 `checksum`(sha256)이 붙는다. 응답 봉투의 `usage`에 AI·검색 호출 수, 어댑터가 보고한 토큰 수, `input_hash`가 담긴다(Execution Logs 기록용). JSON 수정 재시도는 최대 2회. 테스트: `tests/unit`.