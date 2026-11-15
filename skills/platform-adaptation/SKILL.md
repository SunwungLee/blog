# platform-adaptation

- 유형: Script 우선 + AI
- 진입점: `platform_adaptation.py` 의 `run(request, ...)` (공통 JSON 봉투, [DATA_SCHEMA](../../docs/DATA_SCHEMA.md))
- 책임: 승인된 원고를 네이버/블로그스팟 형식으로 변환한다. 사실은 바꾸지 않는다.

## 입력 (`input`)
`article_markdown`, `title`, `platform`(naver|blogspot), `content_type`, `meta_description`?, `adaptation_mode`?(`auto` 기본 | `ai`), `target_platforms[]`?(기본 `[platform]`), `output_version_no`?, `other_platform_output`?, `images[]{image_id,status,url,alt_text,slot_heading?}`?, `blocked_terms`?

## 출력 (`output`)
`adaptation_method`(`script`|`ai`), `title`, `meta_description`, `adaptation_summary`, `warnings[]`(`IMAGE_OMITTED`, `IMAGE_NOT_PLACED`, `DUPLICATE_CHECK_PENDING`), `artifact`(html, `checksum`), `markdown`

## 규칙과 오류
refs: `content_id`. 스크립트 우선(확정, Phase 0 20.13): `auto`에서 blogspot은 SEO 원고의 H2/H3 구조를 그대로 쓰므로 AI 없이 HTML로 변환한다(맨 앞 H1 제거, 이미지는 `slot_heading` 소제목 뒤에 배치). 다른 플랫폼 결과물과 너무 비슷하거나 콘텐츠 규칙에 걸리면 AI로 넘어간다. naver는 말투·문단 재작성이 필요해 항상 AI를 쓴다. 따라서 두 플랫폼 발행 시 AI 호출은 naver 한 번이며, 두 결과물은 서로 다르다. AI 경로: 숫자·링크·고지문 보존 검사(링크·이미지 추가도 금지), 금융 금지·상투 표현·식별정보 검사. 중복 문서 방지: `other_platform_output`이 있으면 그것과의 문장 중복(`max_platform_overlap`)을 검사하고, `target_platforms`에 두 플랫폼이 모두 있는데 다른 결과물이 아직 없으면 원고와의 중복(`max_master_overlap`, AI 경로만)을 검사하고 `DUPLICATE_CHECK_PENDING` 경고를 낸다(다음 플랫폼 생성 시 이 결과를 넘겨야 함). 권리 확인된 이미지만 삽입하고 `{{image:ID}}`가 아닌 Markdown 이미지는 제거. 공개 발행은 하지 않음.

공통: 공급자/모델은 주입(`llm(role, system, prompt)`, `search(query, max_results)`)이며 코드에 하드코딩하지 않는다. 역할(role)은 `config/model-config.json`의 `tasks.<작업>.model`에서 읽는다. 공급자 예외는 `API_TRANSIENT`/`API_RATE_LIMITED`/`AUTH_OR_PERMISSION`으로 변환된다. refs의 `content_id`·`topic_id` 형식이 틀리면 AI 호출 전에 `INVALID_INPUT`. 산출물 `artifact`에는 `checksum`(sha256)이 붙는다. 응답 봉투의 `usage`에 AI·검색 호출 수, 어댑터가 보고한 토큰 수, `input_hash`가 담긴다(Execution Logs 기록용). JSON 수정 재시도는 최대 2회. 테스트: `tests/unit`.