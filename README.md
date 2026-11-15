# 한국어 블로그 콘텐츠 제작 Skills

이 프로젝트는 한국어 블로그 콘텐츠 제작 과정을 독립적인 Python Skill과 결정적 Script로 나누어 지원합니다. 주제 후보 발굴부터 자료 조사, 원고 작성·검증, 플랫폼별 변환, 게시 후 성과 분석까지 단계별로 처리합니다.

각 Skill은 공통 JSON 요청·응답 봉투를 사용하며, AI 모델과 검색 공급자는 코드에 포함하지 않고 실행 시 주입합니다. 주제, 기획, 원고와 플랫폼별 결과물은 사람의 검토·승인을 거칩니다. 공개 발행은 자동으로 하지 않습니다.

## 포함된 Skills

| Skill | 역할 | 주요 입력 → 출력 |
| --- | --- | --- |
| [`topic-discovery`](skills/topic-discovery/SKILL.md) | 편집 맥락에 맞는 한국어 블로그 주제 후보와 검색 근거를 제안합니다. | 편집 맥락·콘텐츠 유형 → 후보, 키워드, 검색 의도, 출처 |
| [`source-research`](skills/source-research/SKILL.md) | 승인된 주제의 출처와 근거 요약을 수집합니다. | 주제·조사 질문 → 출처 메타데이터, 근거 요약, 조사 공백 |
| [`content-planning`](skills/content-planning/SKILL.md) | 주제와 조사 자료를 바탕으로 글의 방향과 구성을 만듭니다. | 주제·조사 자료 → 핵심 메시지, 방향, 목차 |
| [`interview-questioning`](skills/interview-questioning/SKILL.md) | 답변 누락이나 모순을 확인하고 필요한 후속 질문을 만듭니다. | 질문 템플릿·기획·답변 → 미응답 항목, 충돌, 후속 질문 |
| [`master-article`](skills/master-article/SKILL.md) | 승인된 기획, 근거, 사용자 답변으로 기본 원고를 작성합니다. | 기획·조사 출처·답변 → Master Article 및 검토 경고 |
| [`fact-checking`](skills/fact-checking/SKILL.md) | 원고의 주장을 조사 근거와 대조합니다. | 원고·조사 출처 → 주장별 확인 결과, 미해결 주장 |
| [`seo-optimization`](skills/seo-optimization/SKILL.md) | 기계적 SEO 검사를 하고 필요한 경우 제목·메타·본문을 다듬습니다. | 원고·키워드·검색 의도 → SEO 검사 결과, 최적화 원고 |
| [`image-preparation`](skills/image-preparation/SKILL.md) | 이미지 배치 계획과 사용 권리 메타데이터를 준비합니다. | 원고·이미지 자산·제약 조건 → 이미지 계획, 사용 가능 여부 |
| [`platform-adaptation`](skills/platform-adaptation/SKILL.md) | 승인된 원고를 네이버 블로그 또는 Blogspot 형식으로 변환합니다. | 승인 원고·플랫폼 → 플랫폼별 결과물 및 변환 요약 |
| [`performance-analysis`](skills/performance-analysis/SKILL.md) | 게시 성과 지표를 집계하고 개선 제안을 만듭니다. | 측정 지표·게시 정보 → 성과 요약, 개선 제안 |

## 권장 작업 흐름

1. `topic-discovery`에서 후보를 검토하고 사람이 주제를 선택합니다.
2. `source-research` → `content-planning`을 실행하고 사람이 기획을 승인합니다.
3. `interview-questioning` → `master-article`로 답변과 원고를 준비합니다.
4. `fact-checking`으로 근거를 확인하고, 필요한 수정을 반영해 다시 검증합니다.
5. `seo-optimization`을 적용하고 사람이 최종 원고를 승인합니다.
6. `image-preparation` → `platform-adaptation`으로 게시용 결과물을 준비합니다. 실제 공개 발행은 수동으로 진행합니다.
7. 게시 후 수집한 지표가 있으면 `performance-analysis`를 실행합니다.

경험이나 리뷰 글의 개인 경험은 사용자가 제공한 답변만 사용하며, 확인되지 않은 이미지 권리는 사용하지 않습니다. 금융 콘텐츠는 공식 근거와 필수 고지를 적용합니다. 네이버와 Blogspot에는 같은 글을 그대로 복제하지 않습니다.

## 실행

Python 3.12 이상에서 저장소 루트 기준으로 JSON 요청을 표준 입력으로 전달합니다.

```powershell
Get-Content -Raw request.json | python run_skill.py topic-discovery
```

`request.json`은 해당 Skill 문서와 [공통 JSON 계약](docs/DATA_SCHEMA.md)에 맞춰 작성합니다. AI 또는 검색이 필요한 Skill은 `--providers`로 `llm` 및/또는 `search` 함수를 제공하는 Python 모듈을 지정할 수 있습니다.

```powershell
Get-Content -Raw request.json | python run_skill.py topic-discovery --providers my_providers
```

AI·검색 공급자는 현재 저장소에 선택·연결되어 있지 않습니다. 공급자를 제공하지 않은 상태에서 해당 기능이 필요하면 구조화된 오류가 반환될 수 있습니다. API 키 등 비밀 정보는 저장소에 넣지 마세요.

두 CLI는 항상 JSON 봉투 하나를 출력합니다(종료 코드 0은 `output`, 1은 `error`). `--hash-only`를 붙이면 모듈을 실행하지 않고 중복 실행 확인용 `input_hash`만 반환합니다. Workflow 전용 `id-allocator` Script는 `state/` 폴더(또는 `BLOG_ID_STATE_DIR`)에 일련번호를 기록합니다. 자세한 내용은 [오케스트레이션 기반 설계](docs/ORCHESTRATION_FOUNDATION.md)를 참고하세요.

## 테스트

```powershell
python -m unittest discover -s tests/unit
```

구현된 Skill, Script 및 단위 테스트는 Python 표준 라이브러리를 사용합니다. 환경 요건과 선택적 패키지는 [`requirements.txt`](requirements.txt)를 참고하세요.

## 문서

- [프로젝트 시작 안내](docs/PROJECT_START_HERE.md)
- [Skill 사양](docs/SKILL_SPECIFICATION.md)
- [데이터 스키마 및 모듈 계약](docs/DATA_SCHEMA.md)
- [시스템 아키텍처](docs/SYSTEM_ARCHITECTURE.md)
- [오케스트레이션 기반 설계](docs/ORCHESTRATION_FOUNDATION.md)
- [구현 계획](docs/IMPLEMENTATION_PLAN.md)
- [개발 지침](AGENTS.md)
