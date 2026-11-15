# 프로젝트 시작 안내

## 프로젝트 개요

이 프로젝트는 한국어 블로그 콘텐츠 제작 과정을 독립적인 Skill과 결정적 Script로 나누어 보조하는 시스템이다. 주제 후보부터 자료 조사, 기획, 인터뷰, 원고 작성·검증, SEO, 이미지 준비, 플랫폼별 변환, 성과 분석까지 단계별로 처리한다. 주제·기획·원고·플랫폼 결과물은 사람이 검토·승인하며, 시스템은 공개 발행하지 않는다.

상세 기준은 [`Phase_0_design.md`](../Phase_0_design.md)와 [`docs/`](.) 아래 설계 문서다. 에이전트 지침은 [`AGENTS.md`](../AGENTS.md)에 있다.

## 현재 상태

- 10개 Skill과 5개 Script(`id-allocator` 포함)가 Python으로 구현되어 있고, 테스트는 `python -m unittest discover -s tests/unit`으로 실행한다.
- 지정 PC에 Python 3.12.10, Node.js 24.14.1, Git for Windows, n8n 2.47.4와 프로젝트 `.venv`를 준비했다. Pillow 13.0.0 설치 후 단위 테스트 132개가 통과했다.
- AI·검색 공급자와 API 자격증명은 아직 연결하지 않았다. 현재 구현은 호출 가능한 `llm`/`search`를 주입받도록 되어 있다.
- n8n 로컬 계정 설정, 워크플로, Google Sheets/Drive 연동, 실제 공급자 기반 한국어 품질 검증은 아직 진행하지 않았다.
- `requirements.txt`는 필요한 패키지와 환경 요건을 기록한다. 지정 PC의 설치·구성은 사용자 지시가 있을 때만 진행하고, 시작 안내 과정에서 임의로 설치하지 않는다.
- 블로그 맥락 설정이 준비되지 않았다면, 주제 발굴 요청마다 일반적인 블로그 설명을 입력받는다. 식별·민감한 가족 정보는 프롬프트나 검색 요청에 넣지 않는다.

## 권장 진행 순서

1. 저장소의 `AGENTS.md`, `Phase_0_design.md`, `docs/IMPLEMENTATION_PLAN.md`를 확인하고 이미 확정된 결정과 미확정 항목을 구분한다.
2. 지정 PC의 기본 Python/Node/Git/n8n 환경은 준비되어 있다. 추가 패키지 설치와 설정은 `requirements.txt` 및 기능 필요성을 확인하고 사용자 지시에 따라 진행한다.
3. AI·검색 공급자와 비용·약관·자격증명을 안전하게 준비한다. 키는 저장소에 기록하지 않는다.
4. 블로그 맥락과 실행 조건을 준비한 뒤 `topic-discovery`를 실행해 후보와 출처를 검토한다. 사람이 주제를 승인해야 다음 단계로 간다.
5. 승인된 주제로 `source-research` → `content-planning` → 사람의 기획 승인 → `interview-questioning` → `master-article` 순서로 진행한다.
6. `fact-checking`으로 주장을 확인하고, 필요하면 원고를 수정·재검증한다. 통과한 원고에 `seo-optimization`을 적용한 뒤 사람이 최종 원고를 승인한다.
7. `image-preparation`에서 사용권이 확인된 이미지만 선택하고, `platform-adaptation`으로 승인된 원고를 플랫폼별로 변환한다. 플랫폼별 발행 결과물도 사람이 승인하고 실제 공개는 수동으로 한다.
8. 게시 이후 실제로 수집한 지표가 있을 때 `performance-analysis`를 실행한다.
9. 단계별 검증 후에만 추후 n8n, Sheets/Drive 연동을 진행한다. 전체 워크플로를 한꺼번에 자동화하지 않는다.

## 지금 시작할 수 있는 작업

사용자가 진행을 지시하면 먼저 해당 단계의 입력과 선행 조건을 점검하고, 하나의 Skill만 실행·검증한다. 공급자나 필수 입력이 없어 실제 실행이 불가능하면 이를 명시하고, 네트워크/API 연결 없이 할 수 있는 오프라인 테스트를 구분해 안내한다.

## 시작 훅

`.github/hooks/project-start.json`은 Copilot CLI의 새 대화형 세션에서 이 문서를 읽고 개요와 진행 순서를 먼저 안내하도록 요청한다. Copilot CLI의 prompt hook은 세션 재개나 비대화형 실행에서는 동작하지 않을 수 있다. 저장소 훅을 처음 사용할 때는 런타임의 workspace trust와 훅 사용 설정을 확인한다.
