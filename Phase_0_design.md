# 블로그 자동화 시스템 설계 문서

## PHASE 0 - Foundation & Architecture


- 문서 버전: 2.1 (2차 설계 검증 반영)
- 작성일: 2026-11-12
- 프로젝트 상태: PHASE 0 설계 문서 완료 / 개발 환경 설치·구성은 사용자 개인 PC 사용 가능 시까지 보류 / 사용자 지시로 10개 Skill·5개 Script 표준 라이브러리 구현 및 단위 테스트 132개 완료(공급자 연동 없음, 20.12~20.14)
- 개발 방법론: Superpowers
- 목적: 모바일에서 진행한 설계 논의를 PC 개발 환경으로 이전하고, 이후 개발의 기준 문서로 사용

---

# 1. 프로젝트 개요

## 1.1 프로젝트 목표

육아·생활 및 재테크 콘텐츠를 중심으로 콘텐츠 제작의 전 과정을 AI가 지원하고 사람이 주요 결정을 승인하는 반자동 블로그 운영 시스템을 구축한다.

자동화 범위:

1. 콘텐츠 주제 발굴
2. 키워드 및 검색 의도 분석
3. 자료 조사 및 출처 수집
4. 콘텐츠 기획 및 목차 생성
5. 사용자 경험 수집
6. Master Article 작성
7. 사실관계 검증
8. SEO 최적화
9. 이미지 제작 및 관리
10. 플랫폼별 콘텐츠 변환
11. Google Blogspot 임시글 생성
12. 네이버 블로그 발행용 콘텐츠 패키지 생성
13. 콘텐츠 성과 분석

AI가 대부분의 반복적인 콘텐츠 제작 업무를 수행하지만, 사람이 중요한 의사결정과 최종 공개를 승인하는 구조를 지향한다.

## 1.2 프로젝트 운영 방향

- 운영 형태: 반자동 운영형
- 최우선 가치: 콘텐츠 품질과 신뢰성
- 개발 방식: 독립 모듈 개발 후 통합
- 개발 방법론: Superpowers
- AI 활용: 필요한 작업에만 AI 사용
- 토큰 전략: Script 우선, AI는 의미 판단과 창작에 집중

## 1.3 블로그 운영 맥락

- 주요 주제: 육아, 생활 경험, 자녀 관련 재테크 및 금융 정보
- 운영 플랫폼: 네이버 블로그 + Google Blogspot
- 시스템 관리·개발 담당: 시스템 구축과 유지보수를 맡는 사람
- 주요 콘텐츠 작성자: 가족 구성원. AI 활용이 익숙하지 않아도 쉽게 사용할 수 있어야 함
- 문체: 전문성과 따뜻한 육아 공감이 공존하는 존댓말
- 콘텐츠 방향: 개인 경험 기록 + 신뢰할 수 있는 정보 제공

### 콘텐츠 작성 원칙

- 실제 경험을 기반으로 작성한다.
- AI가 사용자의 경험을 임의로 만들어내지 않는다.
- 투자 매수 권유나 근거 없는 수익 예측을 하지 않는다.
- 금융 및 제도 정보는 공식 자료를 우선한다.
- 정보의 기준일과 출처를 명확히 관리한다.
- 전문성과 가독성을 동시에 확보한다.

## 1.4 콘텐츠 준수 사항

- 자녀와 가족의 실명, 얼굴 사진, 위치 등 개인정보는 사람이 공개를 허용한 범위에서만 사용한다.
- 협찬·제휴·광고가 포함된 글에는 그 사실을 표시한다.
- 금융 정보 글에는 투자 권유가 아니라는 안내와 정보 기준일을 넣는다.
- 이미지는 사용 권한이 확인된 것만 쓴다.
- 네이버 블로그와 Google Blogspot에 같은 글을 그대로 올리지 않는다. 플랫폼별 변환 단계에서 중복 문서 문제를 다룬다.

세부 규칙은 19장 미확정 사항으로 두고 상세 설계에서 확정한다.

## 1.5 성공 기준

다음 항목을 기준으로 삼는다. 구체적인 수치는 아직 정하지 않았다. 월 비용 한도는 PHASE 1 구현 착수 전에 정하고(현재는 `topic-discovery` 전용 월 $5 잠정 한도만 승인됨, 20.9 참조), 나머지 수치는 초기 운영 결과를 본 뒤 정한다.

- 발행 편수(주 또는 월 단위)
- 월 AI·API 비용 한도
- 사람이 승인 단계에서 되돌려 보낸 비율

토큰 사용량과 비용은 실행할 때마다 Execution Logs 탭에 기록한다.

---

# 2. 확정된 설계 의사결정

다음 항목은 사용자와 논의하여 확정한 사항이다.

| 번호 | 설계 항목           | 확정 결정                          |
| ---- | ------------------- | ---------------------------------- |
| 01   | 운영 목표           | 반자동 운영형                      |
| 02   | 최우선 가치         | 콘텐츠 품질과 신뢰성               |
| 03   | 주제 선정           | AI가 5~10개 추천, 사람이 최종 선택 |
| 04   | 개발 방식           | 독립 모듈 개발 후 통합             |
| 05   | 데이터 저장소       | Google Sheets                      |
| 06   | 사용자 경험 수집    | 기본 질문 + AI 추가 질문           |
| 07   | 질문 템플릿         | 공통 질문 + 콘텐츠 유형별 질문     |
| 08   | 콘텐츠 유형         | 5개 유형 모두 활성화               |
| 09   | AI 모델 운영        | 작업별 모델 분리(Hybrid)           |
| 10   | 실행 환경           | 로컬 개발 + 24시간 켜두는 개인 PC에서 운영 |
| 11   | 모듈 간 데이터 전달 | Sheets + Drive + n8n + JSON        |
| 12   | 오류 처리           | 오류 유형별 하이브리드 처리        |
| 13   | 사람의 승인         | 품질 중심 승인형                   |
| 14   | 최종 발행           | 반자동 발행                        |
| 15   | 인증정보 관리       | n8n Credentials + 환경변수         |
| 16   | 발행 대상           | 콘텐츠별로 네이버 및 Google Blogspot 중 선택, 필요 시 모두 선택 |
| 17   | 출처 기준           | 공식·원문 우선, 게시일·확인일 기록, 보조 출처로 맥락 보완 |
| 18   | 개인정보 기본값     | 식별 정보는 기본 제외, 글별 명시적 허용 시 최소한으로 사용 |
| 19   | 승인 거부           | 결과물 생성 단계로 돌아가 수정 후 같은 승인 단계에서 재검토 |
| 20   | 승인 거부 재검토    | 횟수를 제한하고 초과 시 담당자 판단 (횟수와 초기화 규칙은 결정 39) |
| 21   | JSON·품질 재실행    | 수정 및 재실행 최대 2회 |
| 22   | 월 비용 한도        | API 후보 비용 산정 후 PHASE 1 시작 전 확정 (`topic-discovery` 전용 월 $5 잠정 한도만 승인됨, 전체 한도는 미확정; 20.9·19장 참조) |
| 23   | 모듈 호출 방식      | n8n이 운영 PC의 로컬 Python/JavaScript 프로그램을 실행하고 표준 JSON으로 통신 |
| 24   | 콘텐츠 식별자       | `TOP-YYYYMMDD-0001`, `CNT-YYYYMMDD-0001`; 내부 행 ID는 UUID |
| 25   | API 재시도          | 일시 오류·호출 한도 초과 모두 최초 호출 후 최대 3회 |
| 26   | 기술 오류 복구      | 재시도 소진 시 FAILED, 운영자 복구 후 실패 단계부터 수동 재개 |
| 27   | 승인 거부 복귀 경로 | 주제→후보 재발굴, 기획→기획 수정, 최종 원고→DRAFTING, 발행 결과는 사유별 처리 |
| 28   | 공개 대기 상태      | 발행 승인 후 WAITING_FOR_MANUAL_PUBLISH, 선택 플랫폼 모두 완료 표시 시 PUBLISHED |
| 29   | Sheets 구조         | 한 행에 한 레코드·ID로 연결, 원고는 버전별 행, Approvals·Interview Responses 탭 사용 |
| 30   | Drive 규칙          | 콘텐츠별 폴더 + 고정 하위 폴더, 파일명은 콘텐츠 ID+자료 종류+버전 |
| 31   | 모듈 JSON           | 공통 봉투(`schema_version`, `run_id`, `module`, `refs`) + 모듈별 `input`/`output` |
| 32   | 운영 PC             | Windows, n8n은 초기 수동 실행 후 안정화되면 자동 시작 |
| 33   | 외부 연결           | 인바운드 Webhook 기본 비활성, 필요할 때만 검토 |
| 34   | 백업                | 암호화 외장 드라이브에 매일 1회, 사용자가 수동 관리 |
| 35   | 접근·보관           | 승인된 가족 작성자·관리자 계정만 공유, 공개 링크 금지, 인터뷰 원문은 콘텐츠 삭제 시 함께 삭제, 승인자는 역할만 기록 |
| 36   | 이미지 소스         | 직접 촬영·사용권 확인 이미지·AI 생성 이미지 허용, 사용 권한 확인 |
| 37   | 주제 단계 기록      | `Discovery Runs` 탭에 발굴 실행 단위로 기록, Content Pipeline은 주제 승인 후 RESEARCHING부터 시작 |
| 38   | 취소 조건           | 사람이 `WAITING_FOR_*` 또는 `NEEDS_REVISION`에서 취소 결정, 자동 취소 없음 |
| 39   | 승인 거부 횟수      | 최초 검토 1회+재검토 최대 3회, 네 번째 거부 시 NEEDS_REVISION; 담당자가 재개하면 횟수 초기화 |
| 40   | 플랫폼 재변환 이력  | `output_version_no`를 올려 Publishing에 새 행 추가, 이전 결과 보존 |
| 41   | 발행 플랫폼 선택 시점 | 기획 승인 시 Content Platforms에 선택 기록 |
| 42   | 기획 상태           | RESEARCHING은 조사, PLANNING은 기획안 작성·수정, PLANNED는 승인 요청 준비 |
| 43   | 발행 결과 거부 처리 | 형식→해당 플랫폼 재변환, 이미지→IMAGE_PREPARING, 사실·핵심 내용→DRAFTING |
| 44   | Blogspot 임시글     | 플랫폼별 발행 승인 후 생성, 기존 임시글이 있으면 갱신 |
| 45   | 성과 분석 상태      | ANALYZING 완료 후 PUBLISHED로 복귀 |

표에 없더라도 본문 각 장에 적힌 규칙(예: 8.4 질문 운영 규칙, SEO를 최종 원고 승인 앞에 두는 순서)은 확정 사항이다.

---

# 3. 초기 콘텐츠 유형

초기 콘텐츠 유형은 다음 5개로 확정한다.

| ID         | 콘텐츠 유형       | 주요 내용                           |
| ---------- | ----------------- | ----------------------------------- |
| experience | 육아·생활 경험담 | 실제 육아 경험, 시행착오, 일상 기록 |
| finance    | 재테크·금융 정보 | 자녀 계좌, 증여, 투자, 금융상품     |
| review     | 제품·서비스 리뷰 | 직접 사용한 제품 및 서비스 후기     |
| guide      | 정보·가이드      | 제도, 신청 방법, 사용 방법          |
| compare    | 비교·분석        | 제품, 금융상품, 서비스 장단점 비교  |

각 콘텐츠 유형에 따라 다음 항목을 차별화한다.

- 질문 템플릿
- 자료 조사 방식
- 콘텐츠 구성
- 사실 검증 기준
- SEO 전략
- 원고 작성 프롬프트

초기에는 5개 유형 모두 활성화하고 실제 운영 데이터를 기반으로 개선한다.

---

# 4. 전체 시스템 아키텍처

## 4.1 기본 구조

시스템은 크게 3개 계층으로 구성한다.

### Layer 1. Script Engine

반복적이고 규칙적인 작업을 담당한다.

주요 기능:

- JSON 데이터 검증
- 데이터 정리 및 중복 제거
- 파일명 생성
- 콘텐츠 글자 수 검사
- 기계적인 SEO 검사
- Markdown / HTML 변환
- 이미지 리사이징
- 파일 저장 및 이동
- 데이터 형식 변환

원칙:

결정적인 작업에는 AI를 사용하지 않는다.

### Layer 2. AI Skill Engine

의미 판단과 창작이 필요한 작업을 담당한다.

주요 기능:

- 콘텐츠 주제 발굴
- 키워드 분석
- 검색 의도 분석
- 자료 조사 결과 종합
- 콘텐츠 기획
- 사용자 답변 분석
- 추가 질문 생성
- Master Article 작성
- 사실관계 검토
- SEO 품질 평가
- 플랫폼별 콘텐츠 변환
- 이미지 기획(허용 소스는 결정 36, 제작 절차는 19장 미확정 사항)
- 콘텐츠 성과 분석

각 기능은 독립적인 Skill로 개발한다.

### Layer 3. Workflow Engine

n8n을 활용하여 전체 실행 흐름을 관리한다.

주요 기능:

- Workflow 실행
- 모듈 간 데이터 전달
- 작업 분기
- 승인 대기
- 재시도
- 오류 처리
- 실행 이력 기록
- 실패 단계부터 재실행

## 4.2 계층별 책임과 경계

| 계층 | 책임 | 경계 |
| ---- | ---- | ---- |
| Script Engine | 결정적인 데이터 검증·변환, 파일 처리, 기계적 검사 | 의미 판단이나 콘텐츠 창작을 맡지 않는다. |
| AI Skill Engine | 주제·검색 의도·기획·원고·사실 검토 등 의미 판단과 창작 | 모델은 설정으로 선택하며, Workflow 전체를 제어하지 않는다. |
| Workflow Engine (n8n) | 실행 순서, 분기, 승인 대기, 재시도·오류 처리, 상태 및 실행 이력 관리 | 콘텐츠 생성·검증 로직을 Workflow 내부에 중복 구현하지 않는다. |

각 모듈은 독립된 책임과 표준 JSON 입출력을 가진다. 모듈 간 연결과 실행 순서는 n8n이 관리하고, 콘텐츠 상태·메타데이터는 Google Sheets, 실제 콘텐츠 파일은 Google Drive에 둔다. 실행 중 전달에 필요한 임시 데이터만 n8n에서 관리한다.

## 4.3 모듈 호출 및 데이터 흐름

1. n8n이 현재 콘텐츠 상태와 필요한 참조 정보를 확인한다.
2. n8n이 필요한 입력만 표준 JSON으로 구성해 운영 PC의 로컬 Python/JavaScript 프로그램을 실행한다.
3. 프로그램은 해당 단계의 결과를 표준 JSON으로 반환한다. 결정적 검사는 Script Engine, 의미 판단·창작은 AI Skill Engine에 맡긴다.
4. n8n은 결과에 따라 다음 단계를 실행하거나 사람의 승인을 기다리고, 상태와 실행 이력을 기록한다. 대용량 원고·조사 자료·이미지는 Google Drive에 두고 참조 정보를 사용한다.
5. 실패하면 완료된 단계를 반복하지 않고 실패 단계부터 이어서 실행한다. 중복 실행과 외부 부작용은 멱등성 규칙으로 방지한다.

JSON의 구체적인 필드·전달 방식, 오류 코드, Drive 파일 저장 호출 방식은 데이터 계약 및 운영 설계에서 확정한다.

---

# 5. AI 모델 운영 전략

## 5.1 확정 방식

작업별 모델 분리(Hybrid).

모든 작업에 동일한 AI 모델을 사용하지 않는다.

## 5.2 작업별 모델 배정 초안

| 작업                | 처리 방식            |
| ------------------- | -------------------- |
| 데이터 정리         | Script               |
| 키워드 분류         | 경량 AI              |
| 검색 의도 분석      | 경량 AI              |
| 콘텐츠 기획         | 고성능 AI            |
| 자료 조사           | 검색 API + AI        |
| 사용자 답변 분석    | 경량 AI              |
| 추가 질문           | 경량 AI              |
| Master Article 작성 | 고성능 AI            |
| 사실관계 검증       | 검색 API + 고성능 AI |
| 기계적 SEO 검사     | Script               |
| SEO 품질 평가       | 경량 AI              |
| 플랫폼 변환         | Script + 필요시 AI   |
| 주제 발굴           | 검색 API + 경량 또는 고성능 AI (품질·비용 테스트 후 선택) |
| 이미지 기획         | Script 우선 + 필요시 AI |
| 성과 분석           | Script 우선 + 필요시 AI |

위 모델 배정은 초기 설계안이며 실제 품질과 비용 테스트를 통해 조정한다.

## 5.3 모델 설정 관리

모델 ID를 코드에 직접 입력하지 않는다.

예시:

config/model-config.yaml

```yaml
models:
  lightweight:
    provider: <to-be-selected>
    model: <to-be-selected>

  high_quality:
    provider: <to-be-selected>
    model: <to-be-selected>

tasks:
  keyword_classification:
    model: lightweight

  content_planning:
    model: high_quality

  master_article:
    model: high_quality

  answer_analysis:
    model: lightweight

  search_intent_analysis:
    model: lightweight

  research_synthesis:
    model: high_quality

  followup_question:
    model: lightweight

  seo_review:
    model: lightweight

  fact_checking:
    model: high_quality

  platform_adaptation:
    model: lightweight

  topic_discovery:
    model: high_quality

  image_planning:
    model: lightweight

  performance_analysis:
    model: lightweight
```
위 예시의 `provider`와 `model` 값은 형식을 보여 주는 자리 표시이며 공급자를 정한 것이 아니다. 실제 공급자와 모델 ID는 구현 시점에 API 지원 여부와 비용을 확인하여 지정한다. 작업별 배정은 초기안이며 품질·비용 테스트로 조정한다.

모델 교체 시 개별 Skill을 수정하지 않고 설정 파일만 변경할 수 있도록 한다.

---

# 6. 실행 환경

## 6.1 확정 방식

Hybrid: 로컬 개발 + 상시 켜두는 개인 PC에서 운영.

### 로컬 PC

- Skill 개발
- Python / JavaScript Script 개발
- 단위 테스트
- 통합 테스트
- 프롬프트 테스트
- 디버깅

### 운영 PC

- n8n 운영
- 자동화 Workflow 실행
- 예약 작업 실행
- API 연동
- 상시 운영 (개인 PC를 24시간 켜 둠)

### 개인 PC 운영 조건

별도의 클라우드 서버나 n8n Cloud를 사용하지 않고, 개인 PC에서 n8n을 상시 실행한다.

초기에는 n8n을 수동 실행하고 안정화 후 자동 시작을 구성한다. 실제 운영 전에 PC 재시작 후 시작 동작, 인터넷 연결, 저장 데이터 백업 및 장애 복구를 확인한다.

운영 PC는 Windows를 사용한다. 외부에서 들어오는 Webhook 연결은 기본적으로 사용하지 않는다. 외부 서비스의 Webhook 또는 OAuth 연동이 꼭 필요한 경우 개인 PC 환경에서 안전하게 연결할 수 있는지 별도로 검증하고, 필요한 경우에만 안전한 원격 연결 방식을 설계한다.

- PC 자원과 n8n 설치·상시 실행 가능 여부
- 초기 수동 실행 후 안정화 단계에서 자동 시작 구성 및 검증
- 인터넷 연결과 외부 API 접근
- n8n에서 로컬 Python/JavaScript 프로그램을 실행할 수 있는 설치 방식과 권한
- Webhook/OAuth 연결 필요 여부 및 안전한 연결 방법
- 암호화된 외장 드라이브에 매일 1회 백업 (수동 운영)
- 복구 테스트 및 장애 복구 절차 (사용자 수동 관리)

---

# 7. 데이터 저장 및 전달 구조

## 7.1 확정 방식

Hybrid.

| 데이터 종류         | 저장 및 전달 위치 |
| ------------------- | ----------------- |
| 콘텐츠 ID 및 상태   | Google Sheets     |
| 콘텐츠 메타데이터   | Google Sheets     |
| 실행 이력           | Google Sheets     |
| 원고 Markdown       | Google Drive      |
| 조사 자료           | Google Drive      |
| 이미지 파일         | Google Drive      |
| 실행 중 임시 데이터 | n8n               |
| 모듈 간 입출력      | 표준 JSON         |

Google Sheets는 메타데이터 및 상태 관리용으로 사용한다.

긴 원고 전문은 Google Sheets 셀에 저장하지 않는다.

## 7.2 Google Sheets 구조 초안

각 탭은 한 행에 한 레코드를 저장하고, 레코드 간 연결은 ID로 관리한다. 반복되는 키워드, 주제 근거 링크, 승인, 대상 플랫폼, 플랫폼 발행, 측정값은 별도 행으로 둔다. 열의 자료형과 검증 규칙은 구현 전 데이터 스키마에서 확정한다.

다음 17개 탭을 구성한다.

1. Topics
2. Topic Keywords
3. Topic Sources
4. Discovery Runs
5. Content Pipeline
6. Content Platforms
7. Research
8. Articles
9. Publishing
10. Approvals
11. Interview Responses
12. Fact Checks
13. Images
14. Performance
15. Settings
16. Execution Logs
17. Question Templates

### Topics

주제 후보 한 건마다 한 행을 둔다. `topic_id`는 `TOP-YYYYMMDD-0001` 형식이며, 날짜별 일련번호는 중앙 발급 과정에서 중복되지 않도록 할당한다. 콘텐츠로 선택되기 전에는 `content_id`를 발급하지 않는다.

| 필드 | 설명 |
| ---- | ---- |
| topic_id | 주제 후보 ID (PK) |
| discovery_run_id | 주제 발굴 실행 ID (Discovery Runs 참조) |
| content_type | 콘텐츠 유형 |
| candidate_title | 추천 제목 |
| search_intent | 검색 의도 |
| rationale | 추천 이유 |
| recommendation_order | 추천 표시 순서 (점수 아님) |
| freshness | `evergreen`, `seasonal`, `timely` |
| requires_firsthand_experience | 실제 작성자 경험이 필요한 주제인지 여부 |
| status | 후보 상태 (`CANDIDATE`, `SELECTED`, `REJECTED`) |
| selected_content_id | 선택된 경우 연결된 콘텐츠 ID |
| created_at | 생성 시각 |

### Topic Keywords

주제 후보와 키워드의 연결을 한 행에 하나씩 기록한다. 필드는 `topic_id`, `keyword`, `keyword_type`(`primary`, `related`), `sort_order`로 구성한다. 후보 하나에 대표 키워드 1개와 연관 키워드 3~5개를 둔다.

### Topic Sources

주제 후보를 발굴할 때 사용한 웹 검색 참고 링크를 한 행에 하나씩 기록한다. 필드는 `topic_source_id`(UUID), `topic_id`, `source_title`, `source_url`, `publisher`, `accessed_at`을 포함한다. 검색 결과 전문이나 snippet은 저장하지 않는다. 이 링크는 주제 탐색 참고자료이며 사실 검증 결과가 아니다. 재무·정책 주제는 공식 출처를 우선한다.

### Discovery Runs

주제 발굴 실행 한 번마다 한 행을 둔다. 주제 승인 전에는 `content_id`가 없으므로 주제 단계의 상태와 거부 횟수를 이 탭에 기록한다.

| 필드 | 설명 |
| ---- | ---- |
| discovery_run_id | 발굴 실행 ID (UUID, PK) |
| status | `IDEA`, `WAITING_FOR_TOPIC_APPROVAL`, `COMPLETED`, `REJECTED`, `NEEDS_REVISION`, `FAILED`, `CANCELLED` |
| attempt_no | 같은 발굴 요청의 회차 (1부터) |
| previous_run_id | 주제 거부로 재발굴한 경우 직전 실행 ID |
| resume_status | `FAILED`·`NEEDS_REVISION`으로 바뀌기 직전 상태 |
| selected_topic_id | 승인된 주제 후보 ID |
| created_at, updated_at | 생성·수정 시각 |

주제 승인은 한 실행의 후보 묶음에 대한 결정이다. `attempt_no`는 최초 발굴 실행을 1로 시작한다. 후보 전체를 거부하면 그 실행과 후보를 `REJECTED`로 종료하고, `previous_run_id`로 이어지는 새 실행을 만들어 `attempt_no`를 올린다. 네 번째 거부에서는 새 실행을 만들지 않고 그 실행을 `NEEDS_REVISION`으로 바꾼다(후보는 `REJECTED`). 담당자가 재개를 정하면 그 실행을 `REJECTED`로 종료하고 `attempt_no`가 1인 새 실행을 만든다. `discovery_run_id`는 Workflow가 Skill을 호출하기 전에 발급한다.

### Content Pipeline

콘텐츠당 한 행으로 현재 상태를 관리한다. `content_id`는 `CNT-YYYYMMDD-0001` 형식이며, 사람이 주제를 승인할 때 발급한다. 행은 주제 승인 시점에 `RESEARCHING` 상태로 만든다.

| 필드 | 설명 |
| ---- | ---- |
| content_id | 콘텐츠 ID (PK) |
| topic_id | 선택된 주제 후보 ID |
| content_type | 콘텐츠 유형 |
| working_title | 현재 작업 제목 |
| current_status | 콘텐츠 현재 상태 |
| current_step | 현재 실행 중이거나 마지막으로 실행한 모듈 이름 |
| resume_status | `FAILED`·`NEEDS_REVISION`으로 바뀌기 직전 상태. 복구·판단 후 돌아갈 기준 |
| current_article_version | 현재 기준 원고 버전 |
| review_rework_count | 사실 검증 실패로 `REVIEWING`에서 `DRAFTING`으로 되돌린 횟수(최대 2, 20.14) |
| created_at, updated_at | 생성·수정 시각 |

`current_status`는 14장의 상태 값을 쓴다.

### Content Platforms

콘텐츠가 발행할 플랫폼마다 한 행을 둔다. 필드는 `content_id`, `platform`(`naver`, `blogspot`), `selected_at`이다. 플랫폼 변환 대상과 `PUBLISHED` 판정은 이 탭을 기준으로 한다. 사용자가 기획 승인할 때 발행 대상을 선택하고 이 탭에 기록한다.

### Research

출처·근거 항목당 한 행을 두고, `research_id`는 UUID로 생성한다. 필드는 `research_id`, `content_id`, `source_title`, `source_url`, `publisher`, `published_at`, `accessed_at`, `source_type`, `evidence_summary`, `source_file_id`, `verification_status`를 포함한다.

### Articles

원고 버전마다 별도 행을 추가하고 이전 버전을 보존한다. 필드는 `article_version_id`(UUID), `content_id`, `version_no`, `article_kind`, `status`, `drive_file_id`, `file_name`, `checksum`, `created_at`, `created_by_run_id`를 포함한다. `article_kind`는 `plan`(기획안), `draft`(초안), `final`(SEO 반영 승인 대상 원고) 중 하나이며 `version_no`는 종류별로 센다. 플랫폼 변환 결과물은 이 탭이 아니라 Publishing 탭에 기록한다.

### Publishing

플랫폼 변환 결과물 한 건마다 한 행을 둔다. 필드는 `publishing_id`(UUID), `content_id`, `platform`, `article_version_id`, `output_version_no`, `status`, `drive_file_id`, `platform_draft_id`, `draft_url`, `human_published_at`, `completed_at`을 포함한다. `content_id`·`platform`·`article_version_id`·`output_version_no` 조합은 한 번만 생성한다. 발행 거부로 같은 원고를 다시 변환하면 `output_version_no`를 올린 새 행을 추가하고 이전 행은 보존한다. 플랫폼별 발행 승인을 받은 뒤 Blogspot 임시글을 만들며, 기존 임시글이 있으면 새로 만들지 않고 갱신한다.

### Approvals

승인 요청 한 회차마다 한 행을 두며, 거부 후 재요청은 새 행으로 보존한다. 필드는 `approval_id`(UUID), `discovery_run_id`, `topic_id`, `content_id`, `platform`, `approval_stage`, `attempt_no`, `artifact_type`, `artifact_ref_id`, `requested_at`, `decision`, `resume_to_status`, `decided_at`, `decided_by_role`, `feedback`을 포함한다. `decided_by_role`은 작성자 또는 관리자로 기록하고 이메일은 저장하지 않는다. `attempt_no`는 1부터 센다. `revision_decision`에서 재개를 선택하면 `resume_to_status`에 재개 상태를 기록하고, 취소하면 `decision`에 취소를 기록한다.

| approval_stage | 연결 키 | artifact_type / artifact_ref_id |
| -------------- | ------- | ------------------------------- |
| `topic` | `discovery_run_id` (승인 시 선택한 `topic_id`도 기록) | `topic_candidates` / `discovery_run_id` |
| `plan` | `content_id` | `plan` / 기획안의 `article_version_id` |
| `article` | `content_id` | `article` / 최종 원고의 `article_version_id` |
| `publish` | `content_id` + `platform` (플랫폼별 한 행) | `platform_output` / `publishing_id` |
| `revision_decision` | `discovery_run_id` 또는 `content_id` | `NEEDS_REVISION`에서 담당자가 내린 판단 (재개 단계 또는 취소) |

### Interview Responses

질문에 대한 답변 한 건마다 한 행을 둔다. 필드는 `response_id`(UUID), `form_response_id`, `content_id`, `question_id`, `question_version`, `question_source`(`template` 또는 `ai`), `question_text`, `answer_text`, `answered_at`을 포함한다. `question_text`에는 답변 당시의 질문 문장을 그대로 남긴다. AI 추가 질문은 템플릿에 없으므로 `question_source`를 `ai`로 하고 `question_id`는 UUID로 발급한다. 사용자가 모른다고 답한 경우 답변값은 문서의 원칙에 따라 `모름`으로 보존한다. `form_response_id`는 Google Forms를 입력 화면으로 확정할 때 쓰는 필드이며, Forms 응답을 `content_id`에 연결하는 방법은 19장 미확정 사항이다.

### Fact Checks

사실 확인한 주장 한 건마다 한 행을 둔다. 필드는 `fact_check_id`(UUID), `content_id`, `article_version_id`, `claim_text`, `result`, `research_id`, `note`, `checked_at`, `created_by_run_id`를 포함한다. `result` 허용값은 fact-checking Skill 설계에서 정한다.

### Images

이미지 한 장마다 한 행을 둔다. 필드는 `image_id`(UUID), `content_id`, `source_type`(`own`, `licensed`, `ai_generated`), `drive_file_id`, `rights_note`, `rights_checked_at`, `status`를 포함한다. 사용 권한을 확인하지 않은 이미지는 발행 결과물에 쓰지 않는다.

### Performance

플랫폼별 측정 항목과 측정 시점마다 한 행을 둔다. 필드는 `metric_id`(UUID), `content_id`, `platform`, `measured_at`, `metric_name`, `metric_value`, `source`를 포함한다.

### Settings

운영자가 직접 바꾸는 운영 설정을 관리한다. 필드는 `setting_key`, `setting_value`, `updated_at`을 포함하며 비밀정보는 저장하지 않는다(12.2 참조).

### Execution Logs

모듈 실행 시도마다 한 행을 둔다. 필드는 `execution_log_id`(UUID), `run_id`(UUID), `module`, `workflow_step`, `discovery_run_id`, `topic_id`, `content_id`, `platform`, `input_hash`, `output_ref`, `status`, `started_at`, `completed_at`, `attempt_no`, `error_code`, `token_usage`, `estimated_cost`를 포함한다. `run_id`는 모듈 호출 한 건의 ID이며 재시도는 같은 `run_id`에 `attempt_no`만 올린다. `input_hash`는 모듈 입력과 적용 설정 버전의 해시다. 같은 `discovery_run_id`(주제 발굴 단계) 또는 `content_id`(이후 단계)·`module`·`input_hash`로 성공한 행이 있으면 다시 실행하지 않고 `output_ref`의 결과를 쓴다. 실패 단계 재개는 `workflow_step`과 Discovery Runs 또는 Content Pipeline의 `resume_status`를 기준으로 한다.

### Question Templates

질문 템플릿의 버전 한 건마다 한 행을 둔다. 필드는 `question_id`, `category`, `content_type`(공통 질문은 비움), `question`, `required`, `sort_order`, `active`, `version`을 포함한다. 키는 `question_id`와 `version`의 조합이다. 질문 문장을 고치면 기존 행을 수정하지 않고 `version`을 올린 새 행을 추가한다.

날짜 기반 ID는 발급일의 `YYYYMMDD`를 사용하고, 시각 값은 시간대 오프셋을 포함한 ISO 8601 형식으로 저장한다. `topic_id`와 `content_id` 외 시스템 내부 레코드 ID는 UUID를 사용한다.

위 필드는 상세 설계 초안이며, 각 열의 필수 여부·자료형·허용값·검증 규칙은 구현 전 데이터 스키마에서 확정한다.

## 7.3 모듈 간 데이터 전달 원칙

모든 모듈은 표준 JSON 규격을 사용한다.

- 모듈 간 직접적인 내부 구현 의존성을 최소화한다.
- 전체 원고를 불필요하게 반복 전달하지 않는다.
- 콘텐츠 ID와 파일 참조를 활용한다.
- n8n은 실행 중 필요한 데이터만 전달한다.
- Sheets에는 상태와 참조 정보를 저장한다.
- Drive에는 실제 콘텐츠 파일을 저장한다.

### 공통 모듈 요청

```json
{
  "schema_version": "1.0",
  "run_id": "UUID",
  "module": "module-name",
  "refs": {
    "discovery_run_id": "UUID",
    "topic_id": "TOP-YYYYMMDD-0001",
    "content_id": "CNT-YYYYMMDD-0001",
    "drive_file_ids": []
  },
  "input": {}
}
```

실행 맥락에 해당하는 ID만 `refs`에 포함한다. 주제 발굴처럼 아직 주제 ID가 없는 요청은 `discovery_run_id`만 포함한다. 긴 원고 전문 대신 Drive 파일 참조와 필요한 발췌문을 전달한다.

### 공통 모듈 응답

성공 응답은 `schema_version`, `run_id`, `module`, `refs`, `output`을 포함한다. 실패 응답은 같은 실행 식별정보와 구조화된 `error` 객체를 반환한다. `error`에는 `code`, `message`, `retryable`을 포함하고, 필요하면 민감정보를 제거한 `details`를 추가한다.

성공 응답 예시:

```json
{
  "schema_version": "1.0",
  "run_id": "UUID",
  "module": "module-name",
  "refs": {},
  "output": {}
}
```

실패 응답은 `output` 대신 `error` 객체를 포함한다.

```json
{
  "schema_version": "1.0",
  "run_id": "UUID",
  "module": "module-name",
  "refs": {},
  "error": {
    "code": "API_TRANSIENT",
    "message": "요청을 완료하지 못했습니다.",
    "retryable": true
  }
}
```

각 AI Skill은 정해진 JSON 입력을 받고 구조화된 JSON 결과를 반환한다. 결과에는 필요한 출처 참조와 경고·미확정 정보를 포함하며, 사용자가 제공하지 않은 실제 경험을 생성하지 않는다. 개별 Skill의 필수 입력·출력 필드는 해당 Skill 설계에서 정의한다.

| Skill | 주요 입력 | 주요 출력 |
| ----- | --------- | --------- |
| topic-discovery | 운영 맥락·선택 콘텐츠 유형·발굴 기준·선택적 제외 목록 | 후보 5~10개, 대표 키워드 1개와 연관 키워드 3~5개, 검색 의도·추천 이유·시기 유형·근거 URL |
| source-research | 승인된 주제·조사 질문·출처 기준 | 출처 메타데이터·근거 요약·Drive 참조 |
| content-planning | 주제·조사 결과 참조·콘텐츠 유형 | 글의 방향·목차·핵심 메시지 |
| interview-questioning | 승인된 기획·질문 템플릿·기존 답변 | 답변 누락·모순, 필요한 경우 추가 질문 1~3개 |
| master-article | 승인된 기획·조사 근거·사용자 경험 답변 | Master Article 및 출처 참조·검토 경고 |
| fact-checking | 원고 버전·조사 근거 | 주장별 확인 결과·근거 참조·미확인 항목 |
| seo-optimization | 원고·키워드·검색 의도 | 검사 결과와 승인 전 최적화 원고 |
| image-preparation | 승인된 기획 또는 원고 참조·이미지 제약 | 이미지 계획·생성/사용 자산 참조·권한 메타데이터 |
| platform-adaptation | 승인된 원고 버전·대상 플랫폼 | 플랫폼별 변환 파일 참조·변환 요약 |
| performance-analysis | 발행 기록·수집한 성과 지표 | 성과 요약·분석 및 개선 제안 |

위 입출력은 모듈 책임을 연결하기 위한 개요다. 필수 필드, JSON 자료형, 콘텐츠 유형별 차이는 각 Skill 설계에서 확정하며, 모든 원고는 `content_id`와 버전 참조로 연결한다.

## 7.4 Google Drive 폴더와 파일명 규칙

승인된 콘텐츠마다 `content_id` 폴더를 만들고 다음 하위 폴더를 사용한다.

```text
content/{content_id}/
├── research/
├── plans/
├── articles/
├── images/
└── publishing/
    ├── naver/
    └── blogspot/
```

파일명은 `{content_id}_{artifact_type}_v{version:03d}.{ext}` 형식으로 하고 콘텐츠 제목은 파일명에 넣지 않는다. 예: `CNT-20261112-0001_master_v001.md`, `CNT-20261112-0001_naver_v001.md`. Drive 파일 ID와 버전 메타데이터는 Sheets에 기록한다. 기획안·초안·최종 원고 파일의 버전은 Articles의 `version_no`, 플랫폼 결과물 파일의 버전은 Publishing의 `output_version_no`를 쓴다.

## 7.5 설정 위치 원칙

같은 설정을 두 곳에 두지 않는다.

| 설정 종류 | 위치 | 관리하는 사람 |
| --------- | ---- | ------------- |
| 질문 템플릿, 운영 중 자주 바꾸는 값 | Google Sheets (Question Templates, Settings) | 콘텐츠 작성자, 관리자 |
| 모델, 재시도, 품질 규칙, 문체 등 기술 설정 | `config/*.yaml` | 개발 담당 |

---

# 8. 질문 템플릿 시스템

## 8.1 기본 원칙

사용자 경험 수집은 사람이 작성한 기본 질문을 중심으로 운영한다.

AI는 답변이 부족한 부분만 추가로 질문한다.

## 8.2 질문 구성

- 공통 질문
- 콘텐츠 유형별 질문
- 필수 질문
- 선택 질문

공통 질문과 유형별 질문을 조합한다.

## 8.3 질문 템플릿 필드

| 필드        | 설명           |
| ----------- | -------------- |
| question_id | 질문 고유 ID   |
| content_type | 공통 질문은 비움, 유형별 질문은 콘텐츠 유형 |
| category    | 질문 유형      |
| question    | 실제 질문 문장 |
| required    | 필수 여부      |
| sort_order  | 표시 순서      |
| active      | 활성 여부      |
| version     | 질문 버전      |

## 8.4 질문 운영 규칙

1. 필수 질문에 답하지 않으면 다음 단계로 넘어가지 않는다.
2. 선택 질문은 건너뛸 수 있다.
3. 이미 답변한 질문은 반복하지 않는다.
4. AI는 답변 누락과 모순을 확인한다.
5. 부족한 부분만 1~3개 추가 질문한다.
6. 사용자가 모른다고 답하면 "모름"을 답변으로 기록하고 다시 묻지 않는다. 필수 질문도 "모름"이면 답한 것으로 본다. AI는 그 내용을 채워 넣지 않는다.
7. AI는 사용자의 실제 경험을 임의로 창작하지 않는다.

---

# 9. 오류 처리 정책

## 9.1 확정 방식

오류 유형별 하이브리드 처리.

오류가 발생했다고 전체 Workflow를 처음부터 다시 실행하지 않는다.

## 9.2 오류 유형별 처리

| 오류 코드 | 상황 | 처리 |
| --------- | ---- | ---- |
| API_TRANSIENT | 일시적인 네트워크·서비스 오류 | 최초 호출 후 최대 3회 재시도 |
| API_RATE_LIMITED | API 호출 한도 초과 | 최초 호출 후 최대 3회 재시도. 제공되면 Retry-After를 따르고, 아니면 설정된 대기 정책 적용 |
| INVALID_JSON | 모듈 응답이 JSON 규격에 맞지 않음 | 수정 요청 후 최대 2회 재검증 |
| QUALITY_BELOW_THRESHOLD | 산출물이 품질 기준 미달 | 해당 모듈만 최대 2회 재실행 |
| INSUFFICIENT_EVIDENCE | 근거 자료 부족 | 자동 재시도하지 않고 NEEDS_REVISION으로 전환해 사람 검토 요청 |
| INVALID_INPUT | 모듈 입력이 규격에 맞지 않거나 식별·민감 정보를 포함 | 자동 재시도하지 않고 NEEDS_REVISION으로 전환해 사람이 입력을 고친 뒤 재개 |
| STORAGE_FAILURE | Sheets/Drive 저장 실패 또는 저장 결과 불명확 | 후속 단계 중단, FAILED 처리 후 운영자 복구 |
| AUTH_OR_PERMISSION | 인증·권한 오류 | 자동 재시도하지 않고 FAILED 처리 |
| UNKNOWN_FAILURE | 분류되지 않은 오류 | 자동 재시도하지 않고 오류 기록 후 FAILED 처리 |

재시도 횟수는 최초 실행과 별개로 센다. 따라서 API 오류의 최대 3회 재시도는 최초 실행을 포함해 총 4회 호출을 뜻한다. JSON 수정과 품질 재실행도 최초 산출물 이후 최대 2회까지다. 재시도 횟수와 대기 정책은 `config/retry-policy.yaml`, 품질 기준은 `config/quality-rules.yaml`에서 관리한다. API 한도 초과는 제공되면 Retry-After를 따르고, 없으면 설정된 exponential backoff를 적용한다. 대기 간격과 최대 대기시간은 공급자 특성을 반영해 설정한다.

JSON 수정이나 품질 재실행 한도를 넘기면 `NEEDS_REVISION`으로 바꾸고 사람 검토를 요청한다. 승인 거부에 따른 수정·재검토는 최대 3회로 제한하며, 초과하면 담당자에게 별도 판단을 요청한다. 기술 오류가 자동 재시도로 해결되지 않으면 `FAILED`로 바꾸고, 운영자가 복구한 뒤 실패 단계부터 수동 재개한다.

품질 미달 판정 기준은 `config/quality-rules.yaml`에서 관리한다.

## 9.3 재실행 원칙

- 완료된 단계는 불필요하게 재실행하지 않는다.
- 실패한 단계부터 재실행한다.
- 변경된 입력과 영향을 받는 후속 단계만 실행한다.
- 동일 작업의 중복 실행을 방지한다.
- 파일과 콘텐츠의 버전을 관리한다.

특히 중복 게시글 생성 등 부작용이 발생하지 않도록 멱등성을 고려한다. 동일한 실행 대상(주제 발굴은 `discovery_run_id`, 이후는 `content_id`)·모듈·입력 버전은 중복 실행하지 않으며, Blogspot 임시글은 `content_id`·플랫폼을 기준으로 기존 Publishing 기록의 `platform_draft_id`를 먼저 확인하고, 있으면 원고 버전이 달라도 그 임시글을 갱신한다. 저장 결과가 불명확하면 확인 전까지 같은 부작용 작업을 다시 실행하지 않는다. 중복 실행 여부는 Execution Logs의 `input_hash`로 확인하며, 13.2의 조사 결과 캐시도 같은 방식으로 찾는다.

---

# 10. 사람의 승인 정책

## 10.1 확정 방식

품질 중심 승인형.

사람의 승인 지점은 4개다.

| 순서 | 승인 단계   | 승인 내용                      |
| ---- | ----------- | ------------------------------ |
| 1    | 주제 선택   | AI 추천 후보 중 최종 주제 선택 |
| 2    | 콘텐츠 기획 | 글의 방향, 목차, 핵심 메시지   |
| 3    | 최종 원고   | 내용, 표현, 사실관계 (SEO 반영본) |
| 4    | 발행 승인   | 플랫폼별 최종 결과물 확인      |

사람이 승인하지 않은 콘텐츠는 다음 단계로 넘어가지 않는다.

나머지 자료 조사, 질문 생성, 초안 작성, SEO 검사, 이미지 준비, 플랫폼 변환은 자동화한다.

최종 원고 승인 이후에는 사실과 핵심 내용을 바꾸지 않는다. 플랫폼 변환은 표현, 구성, 형식만 바꿀 수 있고, 바뀐 결과는 발행 승인에서 사람이 확인한다. 사실이나 핵심 내용을 바꿔야 하면 최종 원고 승인을 다시 받는다.

각 승인 단계는 최초 검토 1회와 재검토 최대 3회까지 진행한다. 최초 검토를 포함해 네 번째 거부가 나오면 `NEEDS_REVISION`으로 바꾸고 담당자가 재개 단계 또는 취소를 정한다. 담당자가 재개를 정하면 해당 승인 단계의 시도 횟수를 1부터 다시 센다. 이 판단은 승인 4곳과 별개의 사람 개입이며 Approvals 탭에 `revision_decision`으로 기록한다.

---

# 11. 최종 발행 방식

## 11.1 확정 방식

반자동 발행(Semi-Automatic).

### Google Blogspot

- API 연동
- 이미지 등록
- 플랫폼별 발행 승인을 받은 뒤 임시글을 생성 (이미 만든 임시글이 있으면 갱신)
- 사람이 최종 확인
- 사람이 Blogspot에서 직접 공개

### 네이버 블로그

- 발행용 원고 생성
- 이미지 패키지 생성
- 사람이 직접 등록
- 사람이 직접 발행

### 발행 완료 기준

- 시스템은 어느 플랫폼에도 글을 공개하지 않는다. 선택된 플랫폼마다 사람이 직접 공개한다.
- WAITING_FOR_PUBLISH_APPROVAL에서 플랫폼별 결과물을 승인한 뒤 WAITING_FOR_MANUAL_PUBLISH로 전환한다. 승인 자체가 공개 동작은 아니다.
- 사람이 공개한 뒤 완료 표시를 하면 Publishing 탭에 플랫폼별로 기록한다.
- 발행하기로 한 플랫폼이 모두 완료 표시되면 콘텐츠 상태를 PUBLISHED로 바꾼다.

실제 API 지원 범위와 플랫폼 정책을 확인한 후 구현한다.

확인되지 않은 비공식 자동화 방식에 의존하지 않는다.

---

# 12. 인증정보 및 보안

## 12.1 확정 방식

혼합형.

### n8n 연동

n8n Credentials 사용.

### Python / JavaScript

환경변수 사용.

### 로컬 개발

.env 파일 사용 가능.

### 개인 PC 운영

개인 PC의 환경변수를 사용한다. 비밀정보를 소스 코드나 공유 폴더에 저장하지 않는다.

## 12.2 보안 규칙

1. API Key를 Google Sheets에 저장하지 않는다.
2. .env 파일을 Git에 커밋하지 않는다.
3. 프롬프트나 Skill 문서에 비밀번호를 직접 넣지 않는다.
4. 개발용과 운영용 인증정보를 분리한다.
5. 설정 파일에는 비밀값 대신 Credential 참조 정보를 저장한다.
6. 로그에 인증정보가 노출되지 않도록 한다.
7. Google Forms·Sheets·Drive는 승인된 가족 작성자와 관리자 계정만 공유하고 공개 링크 공유를 금지한다.
8. 인터뷰 답변 원문은 해당 콘텐츠와 함께 보관하고, 콘텐츠 삭제 시 함께 삭제한다.
9. 승인자 정보는 작성자/관리자 역할만 기록하고 이메일 주소는 저장하지 않는다.

---

# 13. 토큰 및 비용 최적화

프로젝트의 핵심 설계 원칙 중 하나다.

## 13.1 기본 원칙

AI를 적게 사용해도 안정적으로 작동하는 시스템을 만든다.

### Script 우선

다음 작업은 가능한 한 Script로 처리한다.

- 데이터 정리
- 중복 제거
- JSON 검증
- HTML 변환
- 글자 수 계산
- 이미지 처리
- 파일 관리
- 기계적 SEO 검사

### AI 사용

다음 작업에 집중한다.

- 의미 분석
- 검색 의도 분석
- 자료 조사 종합
- 콘텐츠 기획
- 질문 분석
- 원고 작성
- 사실관계 판단
- 품질 평가

## 13.2 최적화 방법

1. 필요한 정보만 AI에 전달한다.
2. 긴 원고 전체 대신 파일 ID와 필요한 발췌문을 전달한다.
3. 동일한 조사 결과는 캐시한다.
4. 데이터 버전과 해시를 활용한다.
5. 변경된 단계만 재실행한다.
6. 경량 모델과 고성능 모델을 구분한다.
7. 가능한 한 구조화된 JSON으로 입출력한다.
8. 품질 검증을 생략하여 토큰을 줄이지 않는다.

---

# 14. 콘텐츠 제작 전체 Workflow

초기 Workflow는 다음과 같이 구성한다.

1. IDEA
2. WAITING_FOR_TOPIC_APPROVAL
3. RESEARCHING
4. PLANNING
5. PLANNED
6. WAITING_FOR_PLAN_APPROVAL
7. INTERVIEWING
8. DRAFTING
9. REVIEWING
10. SEO_PROCESSING
11. WAITING_FOR_ARTICLE_APPROVAL
12. IMAGE_PREPARING
13. PLATFORM_ADAPTATION
14. PUBLISH_READY
15. WAITING_FOR_PUBLISH_APPROVAL
16. WAITING_FOR_MANUAL_PUBLISH
17. PUBLISHED
18. ANALYZING

1~2번은 주제 단계로 Discovery Runs 탭에 기록하고, 3번부터는 Content Pipeline의 `current_status`에 기록한다. PLANNING은 기획안을 작성·수정하는 상태다.

10장의 승인 4곳은 2, 6, 11, 15번 상태에 대응한다.

SEO 처리는 최종 원고 승인 앞에 두어, 사람이 승인한 원고가 그 뒤에 바뀌지 않게 한다.

추가 상태:

- NEEDS_REVISION
- FAILED
- CANCELLED
- REJECTED (Discovery Runs 전용: 후보 묶음이 거부되어 종료된 발굴 실행)

## 14.1 상태 전이 규칙

| 현재 상태 | 조건 | 다음 상태 |
| --------- | ---- | --------- |
| IDEA | 주제 후보 생성 완료 | WAITING_FOR_TOPIC_APPROVAL |
| WAITING_FOR_TOPIC_APPROVAL | 승인 | 발굴 실행은 COMPLETED, 선택 후보는 SELECTED·나머지 후보는 REJECTED, `content_id` 발급 후 Content Pipeline 행을 RESEARCHING으로 생성 |
| WAITING_FOR_TOPIC_APPROVAL | 거부 (1~3번째) | 해당 발굴 실행과 후보를 REJECTED로 종료하고 새 발굴 실행을 IDEA로 생성 (후보 재발굴) |
| WAITING_FOR_TOPIC_APPROVAL | 네 번째 거부 | 후보는 REJECTED, 발굴 실행은 NEEDS_REVISION |
| RESEARCHING | 자료 조사 완료 | PLANNING |
| PLANNING | 기획안 작성 또는 수정 완료 | PLANNED |
| PLANNED | 기획 검토 요청 | WAITING_FOR_PLAN_APPROVAL |
| WAITING_FOR_PLAN_APPROVAL | 승인 (발행 대상 플랫폼 선택 포함) | 선택한 플랫폼을 Content Platforms에 기록한 뒤 INTERVIEWING |
| WAITING_FOR_PLAN_APPROVAL | 거부 | PLANNING (기획 수정) |
| INTERVIEWING | 필수 질문에 답변하거나 `모름`으로 기록 | DRAFTING |
| DRAFTING | 초안 작성 완료 | REVIEWING |
| REVIEWING | 검토 통과 | SEO_PROCESSING |
| REVIEWING | 자동 사실 검증 실패 (QUALITY_BELOW_THRESHOLD, 최초 이후 최대 2회) | DRAFTING |
| REVIEWING | 재작성 한도 초과 또는 근거 부족 | NEEDS_REVISION |
| SEO_PROCESSING | 최종 승인본 준비 완료 | WAITING_FOR_ARTICLE_APPROVAL |
| WAITING_FOR_ARTICLE_APPROVAL | 승인 | IMAGE_PREPARING |
| WAITING_FOR_ARTICLE_APPROVAL | 거부 | DRAFTING (이후 REVIEWING·SEO_PROCESSING 재실행) |
| IMAGE_PREPARING | 이미지 준비 완료 | PLATFORM_ADAPTATION |
| PLATFORM_ADAPTATION | 선택된 플랫폼별 결과물 준비 완료 | PUBLISH_READY |
| PUBLISH_READY | 발행 승인 요청 | WAITING_FOR_PUBLISH_APPROVAL |
| WAITING_FOR_PUBLISH_APPROVAL | 플랫폼별 발행 결과물 승인 | 승인된 Blogspot 결과물의 임시글을 생성하거나 기존 임시글 갱신 |
| WAITING_FOR_PUBLISH_APPROVAL | 선택한 플랫폼 모두 승인 완료 | WAITING_FOR_MANUAL_PUBLISH |
| WAITING_FOR_PUBLISH_APPROVAL | 거부: 표현·구성·형식 문제 | PLATFORM_ADAPTATION (해당 플랫폼만 재변환) |
| WAITING_FOR_PUBLISH_APPROVAL | 거부: 이미지 문제 | IMAGE_PREPARING |
| WAITING_FOR_PUBLISH_APPROVAL | 거부: 사실·핵심 내용 문제 | DRAFTING (최종 원고 승인을 다시 받음) |
| WAITING_FOR_MANUAL_PUBLISH | 선택된 플랫폼 모두 사람이 공개 완료 표시 | PUBLISHED |
| PUBLISHED | 성과 분석 시작 | ANALYZING |
| ANALYZING | 분석 완료 | PUBLISHED |

PUBLISHED는 발행 후 머무는 상태이고 ANALYZING은 성과 분석을 실행하는 동안만 유지한다.

특수 상태의 진입과 복귀:

| 상태 | 진입 | 복귀 |
| ---- | ---- | ---- |
| FAILED | 어느 상태에서든 기술 오류가 재시도 한도를 넘거나 재시도 대상이 아닐 때. 직전 상태를 `resume_status`에 저장 | 운영자가 복구한 뒤 `resume_status`로 되돌려 실패 단계부터 재개 |
| NEEDS_REVISION | JSON 수정·품질 재실행 한도 초과, 근거 부족, 승인 단계의 네 번째 거부. 직전 상태를 `resume_status`에 저장 | 담당자가 재개 단계를 정하면 그 상태로 이동, 취소를 정하면 CANCELLED |
| CANCELLED | 사람이 `WAITING_FOR_*` 또는 NEEDS_REVISION 상태에서 취소를 결정. 시스템은 자동으로 취소하지 않음 | 없음 (종료 상태) |

주제 단계의 FAILED·NEEDS_REVISION·CANCELLED는 Discovery Runs 행에 같은 규칙으로 기록한다. 주제 단계의 NEEDS_REVISION에서 담당자가 재개를 정하면 그 실행을 REJECTED로 종료하고 `attempt_no`가 1인 새 발굴 실행을 IDEA로 만든다. `topic-discovery`가 근거 부족(`INSUFFICIENT_EVIDENCE`)이나 입력 오류(`INVALID_INPUT`)를 반환하면 발굴 실행을 NEEDS_REVISION으로 바꾸고, 사람이 발굴 기준이나 입력을 고친 뒤 재개한다.

승인 거부 후 재요청은 새로운 `Approvals` 행으로 기록한다. 각 승인 단계는 최초 검토 1회와 재검토 최대 3회까지 진행한다. 최초 검토를 포함해 네 번째 거부가 나오면 `NEEDS_REVISION`으로 전환해 담당자 판단을 기다린다. 담당자가 재개를 결정하면 그 승인 단계의 시도 횟수를 1부터 다시 센다. 담당자 판단은 `Approvals` 탭에 `revision_decision`으로 기록한다.

`WAITING_FOR_*` 상태는 사람이 처리할 때까지 유지하며 자동 재시도하지 않는다. 발행 승인은 플랫폼별로 받고, Content Platforms에 등록된 플랫폼 각각에 대해 `Publishing` 기록을 만든다. 시스템은 플랫폼에 공개 게시하지 않는다. 공개 완료 표시는 플랫폼별로 기록하며 모두 완료된 뒤에만 `PUBLISHED`로 전환한다.

근거 부족은 `NEEDS_REVISION`으로 전환해 사람 검토 후 조사 또는 초안 작성 단계부터 재개한다. `FAILED`는 기술 오류에 한정하고, 운영자 복구 후 실패 단계부터 수동 재개한다. 실패 응답의 `error.code`는 9.2 표의 공통 코드를 사용하며 인증정보 등 비밀값을 `message`나 `details`에 기록하지 않는다.

---

# 15. 프로젝트 폴더 구조 초안

```
blog-automation/
│
├── Phase_0_design.md
├── requirements.txt
│
├── docs/
│   ├── SYSTEM_ARCHITECTURE.md
│   ├── DATA_SCHEMA.md
│   ├── SKILL_SPECIFICATION.md
│   ├── TOKEN_OPTIMIZATION.md
│   ├── IMPLEMENTATION_PLAN.md
│   ├── TOPIC_DISCOVERY_DESIGN.md
│   └── TOPIC_DISCOVERY_WRITING_PLAN.md
│
├── config/
│   ├── blog-context.yaml
│   ├── writing-style.yaml
│   ├── quality-rules.yaml
│   ├── model-config.yaml
│   └── retry-policy.yaml
│
├── skills/
│   ├── topic-discovery/
│   ├── source-research/
│   ├── content-planning/
│   ├── interview-questioning/
│   ├── master-article/
│   ├── fact-checking/
│   ├── seo-optimization/
│   ├── image-preparation/
│   ├── platform-adaptation/
│   └── performance-analysis/
│
├── scripts/
│   ├── data-validator/
│   ├── seo-checker/
│   ├── html-converter/
│   └── image-processor/
│
├── workflows/
│   ├── topic-discovery/
│   ├── content-production/
│   ├── publishing/
│   └── performance-analysis/
│
└── tests/
    ├── unit/
    ├── integration/
    └── fixtures/
```
위 구조는 초기 제안이며 실제 모듈의 책임과 개발 순서에 맞춰 조정한다. 현재 PHASE 0 결정 기록은 프로젝트 루트의 `Phase_0_design.md`에 두고, 상세 문서는 `docs/`에 분리한다.

---

# 16. Superpowers 개발 방법론

전체 개발은 다음 순서로 진행한다.

1. Brainstorming
2. Design Document
3. Writing Plans
4. TDD 기반 Implementation
5. Code Review
6. Verification
7. Finishing Development Branch

각 Skill을 개발할 때도 Writing Skills의 TDD 원칙을 적용한다.

### Skill 제작 절차

1. Skill 없이 작업을 수행하여 실패 사례를 확인한다. (RED)
2. 실패를 방지하는 최소한의 Skill 지침을 작성한다. (GREEN)
3. 동일 시나리오를 다시 실행해 검증한다.
4. 불필요한 지침을 제거하고 개선한다. (REFACTOR)
5. Skill이 안정화되면 다음 Skill로 이동한다.

모든 Skill을 한 번에 만들지 않는다.

독립적인 책임과 명확한 입출력을 기준으로 우선순위를 정하고 하나씩 완성한다.

---

# 17. 다음 개발 단계

PHASE 0의 주요 의사결정은 완료됐다.

다음 일정은 개발 환경 구축이다. 필요한 환경 요건만 `requirements.txt`에 기록했으며, 설치·설정은 사용자의 개인 운영 PC에서만 진행한다. 현재 작업 환경은 개인 PC가 아니므로 이 환경에서는 설치·설정하지 않는다.

## 권장 진행 순서

### STEP 1. PHASE 0 상세 설계 (완료)

- 시스템 아키텍처 확정
- 데이터 구조 상세화
- 공통 JSON 봉투 정의 (정식 JSON Schema는 19장 미확정)
- Skill 공통 규격 정의
- 오류 및 상태 전환 규칙 확정
- 가족 구성원용 입력·승인 화면 방향 정리 (Forms + Sheets 우선 검토, 세부 흐름은 19장 미확정)
- 19장 미확정 사항 중 상세 설계에 필요한 항목 확정

PHASE 0 기준 문서와 상세 문서 패키지를 정리했다. 공급자·연동 세부 사항 등은 19장에 남긴 대로 관련 구현 전에 확정한다.

### STEP 2. 개발 환경 구축 (사용자 개인 PC 사용 가능 시까지 보류)

- Git 저장소 구성
- 로컬 개발 환경 구축
- n8n 개발 환경 구축
- 환경변수 및 인증정보 구성
- 테스트 환경 구성

### STEP 3. PHASE 1 시작

첫 번째 모듈인 `topic-discovery` 설계를 시작한다. 1~5번은 설치·API 호출 없이 먼저 진행할 수 있어 초안을 작성했다(20.10). 6번 이후의 구현은 개인 PC 환경 검증, 모델·검색 공급자 선택, 설계 승인이 끝난 뒤 시작한다.

진행 방법:

1. Superpowers Brainstorming
2. 요구사항 및 예외 상황 정리
3. Skill 책임과 입출력 정의
4. Design Document 작성
5. Writing Plan 작성
6. TDD 기반 구현
7. 독립 테스트
8. 모듈 완성 후 통합 준비

---

# 18. 개발 시 반드시 지켜야 할 원칙

1. 모든 기능을 한 번에 개발하지 않는다.
2. 독립 모듈을 하나씩 완성한다.
3. 모듈 간 연결은 표준 JSON 규격을 사용한다.
4. 반복 작업은 Script로 처리한다.
5. AI는 의미 판단과 창작에 집중한다.
6. 토큰 사용량을 지속적으로 기록한다.
7. 품질과 신뢰성을 비용보다 우선한다.
8. 실제 경험을 AI가 만들어내지 않는다.
9. 금융 정보는 공식 근거를 우선한다.
10. 사람의 승인 없이 공개 발행하지 않는다.
11. 실패한 모듈부터 재실행할 수 있어야 한다.
12. 모델 및 외부 서비스 변경에 유연한 구조를 유지한다.
13. 각 일정 단계가 끝날 때 관련 Markdown 문서를 생성하거나 갱신하고, 결정 사항과 미확정 사항을 반영한다.

---

# 19. 현재 미확정 사항

다음 사항은 아직 확정하지 않았다.

- 작업별 AI 모델 역할과 설정 규격은 설계하되, 실제 모델 ID 및 공급자는 구현 직전에 API 지원 여부와 비용을 확인하여 선택한다.
- 검색 API는 필요한 기능·출처 품질·비용 기준을 정한 뒤 관련 모듈 설계 시 후보를 비교해 선택한다.
- n8n 설치 방식·초기 수동 실행에서 자동 시작으로 전환하는 구체 절차, 로컬 프로그램 실행 권한 (날짜 일련번호 발급의 중복 방지는 20.14에서 확정)
- Google OAuth 및 외부 Webhook이 실제 필요한지, 필요한 경우 안전한 연결 방식
- 수동 일일 백업에 포함할 정확한 항목과 복구 실행 절차
- Google Sheets 필드의 자료형·필수 여부·허용값·검증 규칙
- Drive 접근 권한, 저장 호출 방법 및 파일 보존 정책
- 표준 JSON Schema의 정식 정의·검증 방법과 모듈 호출 시 전달 방식
- Skill별 구체 필드·자료형 및 콘텐츠 유형별 입출력 차이 (공통 봉투와 책임 개요는 7.3 참조)
- API 공급자별 대기 간격·최대 대기시간 및 오류 코드와 외부 오류의 대응
- Google Blogspot(Blogger API) 연동 세부 구현
- Google Blogspot 이미지 등록 방식(API 지원 범위 확인 필요)
- 네이버 블로그 발행 패키지 형식
- 성과 분석 데이터 수집 방식
- 승인 거부 시 수정 담당자와 재검토 운영 역할
- Google Forms 입력 + Google Sheets 승인의 세부 흐름, Forms 응답을 `content_id`에 연결하는 방법, 알림 방식
- 이미지 제작 절차(촬영·생성·선정을 누가 어떻게 하는지)
- 콘텐츠 삭제 절차와 CANCELLED와의 관계(인터뷰 원문 삭제 시점 포함)
- 월 비용 한도를 넘었을 때의 동작(중단 또는 알림)
- 직접 촬영·사용권 확인 이미지·AI 생성 이미지의 권리 확인 세부 절차
- 품질 미달 판정 기준
- 성공 기준 수치(발행 편수, 승인 단계에서 되돌려 보낸 비율; 수치는 초기 운영 결과를 보고 정함)
- `topic-discovery` 모델·검색 공급자와 전체 월 비용 한도 (20.9의 `topic-discovery` 전용 잠정 한도만 사용자 승인됨)
- 결정 22의 "PHASE 1 시작 전 한도 확정"을 `topic-discovery` 전용 한도로 충족한 것으로 볼지 여부 (20.11의 작업 해석, 사용자 확인 필요)
- `topic-discovery` 설계 초안의 미확정 항목: 기본 후보 수 5개, 요청 수 미달 시 부분 목록 반환, 실행당 검색 횟수, 출처 관련성·공식성 판정 기준, 제외 목록 구성 방법 (20.10 참조)
- 검색 공급자 약관이 Topic Sources의 링크 저장을 허용하는지 여부 (Gemini Google Search grounding은 제한 조항이 있어 선택 전 검토 필요)
- 개인정보, 광고 표시, 금융 면책 문구의 세부 규칙
- 네이버 블로그와 Google Blogspot 간 중복 문서 대응 방식

이 항목은 다음 설계 단계에서 검토하고 확정한다.

---

# 20. 상세 설계 진행 기록

## 20.1 PHASE 0 문서 검토

2026-11-12에 문서를 검토했다. 확정된 결정 간 직접적인 충돌은 확인되지 않았다. 상세 설계에서 다음 내용을 구체화한다.

- 승인 거부 시 상태 전이와 수정 담당
- 발행 플랫폼 선택 및 중복 임시글 방지
- 출처 신뢰도·최신성 판단과 사실 확인 결과 저장
- 개인정보 접근 권한, 백업 보관·복구, 로그의 민감정보 처리
- 단계별 통과 조건과 모듈 독립 테스트 완료 조건

## 20.2 사용자와 추가로 정한 기준

- AI 공급자와 모델 ID는 지금 고정하지 않는다. 작업별 역할·설정 규격을 설계하고, 실제 모델은 구현 직전에 지원 여부와 비용을 확인해 선택한다.
- 검색 API 공급자는 지금 고정하지 않는다. 기능·출처 품질·비용 기준을 정하고 관련 모듈 설계 시 비교한다.
- 질문 입력은 Google Forms, 승인 작업은 Google Sheets 조합을 우선 검토한다.
- 플랫폼은 콘텐츠별로 선택하며 네이버와 Google Blogspot을 모두 지정할 수 있다.
- 조사 자료는 공식·원문 출처를 우선하고 게시일·확인일을 기록하며, 보조 출처로 맥락을 보완한다.
- 가족 식별 정보는 기본 제외한다. 글마다 명시적으로 허용된 경우에만 최소한으로 사용한다.
- 승인 거부는 결과물 생성 단계로 돌아가 수정한 뒤 같은 승인 단계에서 재검토한다. 최초 검토 1회와 재검토 최대 3회 후 담당자에게 별도 판단을 요청한다.
- JSON 수정 요청과 품질 미달 재실행은 최대 2회로 한다. API 일시 오류 재시도는 최대 3회로 유지한다.
- 월 AI·API 비용 한도는 후보별 비용을 산정한 뒤 PHASE 1 시작 전에 확정한다.

## 20.3 시스템 아키텍처 상세화

- Script Engine은 결정적 처리, AI Skill Engine은 의미 판단·창작, n8n Workflow Engine은 실행 흐름과 상태·승인을 담당한다.
- 모듈은 독립된 책임과 표준 JSON 입출력을 갖고, n8n이 모듈 간 실행과 전달을 관리한다.
- n8n은 운영 PC의 로컬 Python/JavaScript 프로그램을 실행하는 방식으로 모듈을 호출한다.
- Google Sheets는 상태·메타데이터·실행 이력, Google Drive는 콘텐츠 파일, n8n은 실행 중 임시 데이터를 담당한다.
- 공통 JSON 봉투, 데이터 개요, 오류 분류, 상태 전이를 상세화했다. 실제 전송 방식, Drive 저장 호출 및 로컬 프로그램 실행 권한은 환경 구축 단계에서 검증한다.

## 20.4 데이터·모듈 규격 정의

- `topic_id`는 `TOP-YYYYMMDD-0001`, `content_id`는 `CNT-YYYYMMDD-0001` 형식으로 한다. 내부 레코드 ID는 UUID를 사용한다.
- Sheets는 한 행에 한 레코드를 두고 ID로 연결한다. 반복되는 키워드, 플랫폼별 발행정보, 승인 이력은 별도 행으로 둔다.
- 승인된 콘텐츠마다 Drive 폴더와 `research`, `plans`, `articles`, `images`, `publishing/naver`, `publishing/blogspot` 하위 폴더를 만든다. 파일명에는 콘텐츠 ID·자료 종류·버전을 쓰고 제목은 포함하지 않는다.
- 원고는 버전별 행으로 보존한다. 승인 요청·결정은 회차별 `Approvals` 행으로, 주제 승인 단계는 `discovery_run_id`, 이후에는 `content_id`로 연결한다. 인터뷰 답변은 `Interview Responses` 탭에 기록한다.
- 모듈 요청은 `schema_version`, `run_id`, `module`, `refs`, `input` 공통 봉투를 사용한다. 성공 응답은 `output`, 실패 응답은 구조화된 `error`를 반환한다.
- 상세 컬럼 검증, 정식 JSON Schema, 공급자 오류와 공통 코드의 대응, 전송 방식, 저장 권한, Skill별 필드와 날짜 일련번호 발급의 동시성 제어는 후속 설계에서 확정한다.

## 20.5 Workflow·오류 규칙

- 승인 거부 시 주제는 후보 재발굴, 기획은 기획 수정, 최종 원고는 DRAFTING으로 돌아가 REVIEWING·SEO_PROCESSING을 다시 거친다. 발행 결과 거부는 표현·구성·형식 문제면 해당 플랫폼만 재변환하고, 이미지 문제면 IMAGE_PREPARING, 사실·핵심 내용 문제면 DRAFTING으로 돌아가 최종 원고 승인을 다시 받는다.
- API 일시 오류·호출 한도 초과는 최초 요청 후 최대 3회 재시도한다. JSON 수정·품질 재실행은 최초 산출물 뒤 최대 2회, 승인 단계는 최초 검토 1회+재검토 최대 3회로 한다.
- 호출 한도 초과 시 Retry-After가 있으면 따르고, 없으면 설정된 exponential backoff를 적용한다. 실제 대기 간격과 최대 대기시간은 API 후보 확정 후 설정한다.
- `NEEDS_REVISION`은 콘텐츠·근거 검토가 필요한 경우, `FAILED`는 기술 오류 후 운영자 복구가 필요한 경우에 사용한다. 기술 오류는 복구 후 실패 단계부터 수동 재개한다.
- 발행 승인은 결과물 확인 단계다. 이후 `WAITING_FOR_MANUAL_PUBLISH`에서 사람이 플랫폼별 공개를 완료 표시하고, 선택한 플랫폼이 모두 완료된 경우에만 `PUBLISHED`로 전환한다.
- 동일 실행 대상(주제 발굴은 `discovery_run_id`, 이후는 `content_id`)·모듈·입력 버전은 중복 실행하지 않으며, Blogspot 임시글 생성·갱신 전 Publishing 기록으로 기존 결과를 확인한다.

## 20.6 사용자·운영 요건

- 운영 PC는 Windows이며 n8n은 초기에는 수동 실행하고 안정화 후 자동 시작을 구성한다.
- 외부 인바운드 Webhook은 기본 비활성화하고, 기능상 꼭 필요한 경우에만 안전한 연결을 검토한다.
- 승인 대기와 추가 질문 알림 방식은 운영 환경 구축 단계에서 결정한다.
- 백업은 암호화 외장 드라이브에 매일 1회 두며, 백업과 복구 테스트는 사용자가 수동 관리한다.
- Forms·Sheets·Drive 접근은 승인된 가족 작성자와 관리자 계정으로 제한하고 공개 링크를 금지한다. 인터뷰 원문은 콘텐츠 삭제 시 함께 삭제한다.
- 이미지 소스는 직접 보유한 이미지, 사용권을 확인한 이미지, AI 생성 이미지를 허용하되 사용 권한을 확인한다.
- 승인 이력에는 승인자 역할만 기록하고 Google 계정 이메일은 저장하지 않는다.

## 20.7 PHASE 0 문서 패키지

`Phase_0_design.md`를 확정 결정과 미확정 사항의 기준 문서로 유지한다. 상세 설계 문서는 다음과 같이 분리했다.

- [SYSTEM_ARCHITECTURE.md](docs/SYSTEM_ARCHITECTURE.md): 엔진 책임, 실행·데이터 흐름, 승인 경계
- [DATA_SCHEMA.md](docs/DATA_SCHEMA.md): Sheets 레코드, Drive 규칙, JSON 봉투
- [SKILL_SPECIFICATION.md](docs/SKILL_SPECIFICATION.md): Skill 책임, 공통 규칙, I/O 개요
- [TOKEN_OPTIMIZATION.md](docs/TOKEN_OPTIMIZATION.md): AI/Script 분리, 모델 라우팅, 비용 측정
- [IMPLEMENTATION_PLAN.md](docs/IMPLEMENTATION_PLAN.md): 환경 구축, PHASE 1 게이트, 구현 순서

문서 패키지는 설계 기준선이며, 19장에 남긴 공급자·연동·운영 세부 사항은 관련 구현 전 확정한다. 개발 환경 구축은 다음 일정에서 진행한다.

## 20.8 설계 검토 및 확정 보완

Fable 5.2 서브에이전트가 기준 문서와 분리 문서 5개를 검토했다. 발견한 상태 전이와 데이터 구조의 공백을 보완했으며 사용자가 2026-11-12에 다음 권장안 8개를 확인하여 확정했다.

1. 사람이 `WAITING_FOR_*` 또는 `NEEDS_REVISION` 상태에서 취소할 수 있고 시스템은 자동 취소하지 않는다.
2. 승인 단계는 최초 검토 1회와 재검토 최대 3회로 한다. 네 번째 거부에서 `NEEDS_REVISION`으로 전환하며, 담당자가 재개를 정하면 승인 시도 횟수를 1부터 다시 센다.
3. 같은 원고의 플랫폼 재변환은 `output_version_no`를 올려 Publishing에 새 행으로 보존한다.
4. 발행 대상 플랫폼은 기획 승인 시 선택해 Content Platforms에 기록한다.
5. `RESEARCHING`은 자료 조사, `PLANNING`은 기획안 작성·수정, `PLANNED`는 승인 요청 준비 상태로 구분한다.
6. 발행 결과 거부는 사유별로 처리한다: 표현·구성·형식은 해당 플랫폼 재변환, 이미지 문제는 `IMAGE_PREPARING`, 사실·핵심 내용 변경은 `DRAFTING`으로 되돌려 최종 원고 승인을 다시 받는다.
7. Blogspot 임시글은 플랫폼별 발행 승인 후 생성하고 기존 임시글이 있으면 갱신한다.
8. 성과 분석이 끝나면 `PUBLISHED`로 복귀한다.

검토 과정에서 추가로 보완한 데이터 구조와 분리 문서 변경 내역은 2장 결정표, 7장, 9장, 14장 및 `docs/` 문서에 반영했다. Google Forms 입력 + Google Sheets 승인 조합은 기존 사용자 선택에 따라 우선 검토하되, 세부 흐름과 알림은 19장에 남긴다.

## 20.9 모델·검색 API 예비 비용 검토

2026-11-12 기준, 사용자는 `topic-discovery` 실행량을 월 30회로 추정하고 이 Skill 전용 월 $5 잠정 한도를 승인했다. 입력 10,000토큰·출력 2,000토큰, 실행당 Tavily Advanced 검색 최대 2회 가정에서 `gpt-5.4-mini` 또는 `gemini-3.8-flash` 후보의 모델·검색 비용은 검색 무료 크레딧이 없다고 가정해도 월 약 $1.41~$1.86으로 추산된다(Gemini 현행가 $1.41, GPT-5.4-mini $1.46, 2027-01-01 인상 후 Gemini $1.86). 이 추정에는 재시도·JSON 수정·품질 재실행, 주제 거부에 따른 재발굴, 모델의 추론 토큰 증가분이 들어 있지 않다. 승인된 금액은 전체 시스템의 월 비용 한도가 아니며, 한도 초과 시 중단할지 알릴지는 여전히 미정이다.

모델과 검색 공급자는 확정하지 않았다. 두 후보 모델이 5.3의 `lightweight`와 `high_quality` 중 어느 역할을 맡을지도 정하지 않았으며, 5.3 예시의 `topic_discovery: high_quality`는 자리 표시다. 한국어 결과 품질·출처 품질을 비교하고 실제 API 조건 및 가격을 구현 전에 다시 확인한다. Google Gemini 무료 사용 구간에는 개인·민감 정보 입력을 금지하고, Google Custom Search JSON API는 신규 고객 가입이 닫혀 있어 후보에서 제외한다. 상세 가격, 가정, 공식 출처는 [TOKEN_OPTIMIZATION.md](docs/TOKEN_OPTIMIZATION.md)에 기록했다.

## 20.10 `topic-discovery` 설계 논의

사용자가 환경 설치·구성 없이 진행 가능한 Skill 설계를 요청해 `topic-discovery` 설계 초안을 시작했다. 다음 사항을 논의해 반영했다.

- 키워드 발굴은 별도 Skill이 아니라 `topic-discovery` 책임에 포함한다.
- 웹 검색 결과를 최신 주제 맥락과 후보별 근거 링크에 사용하되 검색량·경쟁도·트렌드 순위를 수치로 주장하지 않는다.
- 각 후보는 관련 URL을 최소 1개 포함한다. 근거를 갖춘 후보가 5개 미만이면 성공 모양의 부분 목록 대신 구조화 오류를 반환한다.
- 후보마다 대표 키워드 1개와 연관 키워드 3~5개를 둔다.
- 콘텐츠 유형은 요청에서 하나 이상 지정할 수 있고, 미지정 시 활성 유형 전체를 사용한다. 여러 유형을 요청하면 가능한 경우 유형별 후보를 먼저 포함한다.
- 숫자 점수는 표시하지 않고 후보 배열 순서와 추천 이유로 우선순위를 표현한다.
- 에버그린 주제를 중심으로 유용한 시즌·시기성 아이디어를 포함하고 유형을 표시한다.
- 기존 후보와의 중복 회피는 요청에 전달된 제외 목록만 대상으로 한다.

초안 기본 후보 수는 기존 확정 범위(5~10개) 안에서 5개로 두었다. 요청 수보다 적더라도 근거를 갖춘 후보가 5개 이상이면 부분 목록과 경고를, 5개 미만이면 오류를 반환하는 안은 설계 초안으로 두고 최종 검토한다. 모델·검색 공급자와 요청당 검색 횟수, 공식 출처·관련성 판정 기준 및 전체 데이터 계약은 미확정이다. 오류 코드와 상태 매핑은 20.11에서 9.2·14.1에 맞췄다. 월 $5 한도는 `topic-discovery` 전용이며 두 번의 Tavily Advanced 검색을 가정한 예비 산정이라 실제 검색 예산은 구현 전 검증한다. 상세 초안은 [TOPIC_DISCOVERY_DESIGN.md](docs/TOPIC_DISCOVERY_DESIGN.md), [TOPIC_DISCOVERY_WRITING_PLAN.md](docs/TOPIC_DISCOVERY_WRITING_PLAN.md)에 있다. 둘 다 설계 초안이며 구현 승인이 아니다.

## 20.11 2차 설계 검증 반영

2026-11-12에 Fable 5.2 서브에이전트가 문서 9개를 읽기 전용으로 검증해 Medium 8건, Low 11건을 보고했다. 사용자가 판단을 맡겨 다음과 같이 고쳤다. 아래 항목은 사용자가 개별 확인한 결정이 아니라 기존 확정 사항에 맞춘 정리이며, 다르게 정하고 싶으면 바꿀 수 있다.

- 오류 코드: `topic-discovery`의 근거 부족은 9.2의 `INSUFFICIENT_EVIDENCE`를 그대로 쓰고, 입력 규격·개인정보 검증 실패용으로 `INVALID_INPUT`을 9.2에 추가했다. 둘 다 발굴 실행을 `NEEDS_REVISION`으로 바꾼다.
- 발굴 실행 종료 상태: Discovery Runs에 `REJECTED`를 추가했다. 주제 거부 시 해당 실행과 후보를 `REJECTED`로 종료하고, 네 번째 거부는 `NEEDS_REVISION`, 담당자 재개 시 `attempt_no`가 1인 새 실행을 만든다(결정 39의 횟수 초기화와 같은 규칙).
- 모듈 요청 봉투의 `refs`에 `discovery_run_id`를 추가했다. Workflow가 Skill 호출 전에 발급한다.
- Blogspot 임시글 확인 기준을 `content_id`·플랫폼으로 통일했다(결정 44).
- 20.4의 승인 연결 키와 Drive 하위 폴더 요약을 7장에 맞췄다.
- 공급자 선택 순서: Writing Plan에서 후보 압축을 먼저 하고 최종 선택은 한국어 품질 비교 뒤로 옮겼다.
- Gemini Google Search grounding 약관에는 링크의 자동 수집·저장을 제한하는 조항이 있어 Topic Sources 저장과 맞지 않을 수 있다. 후보에서 빼지는 않고 선택 전 약관 검토 대상으로 표시했다.
- 비용 게이트의 작업 해석: 결정 22의 "PHASE 1 시작"은 구현 착수를 뜻하는 것으로 읽고, `topic-discovery` 구현은 승인된 Skill 전용 월 $5 한도로 진행할 수 있다고 보았다. 전체 시스템 한도는 나머지 Skill 비용을 산정한 뒤 정한다. 이 해석은 사용자 확인이 필요해 19장에 남겼다.
- 그 밖에 중복 항목, 오래된 상태 문구, 폴더 구조, 비용 범위·여유 배수 표기를 정리했다.

## 20.12 구현 코드 리뷰·설계 점검 반영

사용자 지시로 환경 게이트 전에 10개 Skill·4개 Script·공통 코드를 표준 라이브러리 Python으로 작성했다(공급자 어댑터·API 호출·n8n·Sheets/Drive 연동은 없음). 그 뒤 서브에이전트 2개가 읽기 전용으로 코드 리뷰와 설계 적합성 점검을 하고, 발견 사항을 다음과 같이 고쳤다. 아무것도 설치하지 않았고 단위 테스트는 107개가 통과한다.

- 개인정보: 전화·주민번호 패턴의 경계 오류를 고치고 주소 패턴을 좁혔다. 게시물별 차단어 `blocked_terms`를 모든 콘텐츠 Skill이 받으며, 인터뷰 답변은 프롬프트에 넣기 전에 가린다.
- 고지·금융 규칙을 `common/rules.py`로 모았다. 고지문은 정확한 문장으로 검사하고, 정보 기준일은 입력 `information_as_of` 또는 인용 출처의 최신 확인일을 쓴다. 광고 고지는 `sponsored=true`일 때만 넣는다.
- 사실 보존: 숫자·링크·이미지 추가와 고지문 삭제를 검사한다. SEO는 제목·메타만 실패하면 본문을 보내지 않고, 본문이 바뀌면 `requires_refactcheck=true`로 승인 전 사실 확인을 다시 하게 한다.
- 중복 문서 방지: 두 플랫폼을 모두 대상으로 하는데 다른 결과물이 아직 없으면 원고와의 중복을 검사하고 `DUPLICATE_CHECK_PENDING` 경고를 낸다.
- 오류 계약: 공급자 예외를 `API_TRANSIENT`/`API_RATE_LIMITED`/`AUTH_OR_PERMISSION`으로 변환하고, `refs` 형식 오류는 AI 호출 전 `INVALID_INPUT`으로 막는다. 산출물에 `checksum`을 붙인다.
- fact-checking은 `article_version_id`를 필수로 받고 `created_by_run_id`를 기록한다. `passed=false`는 성공 응답이며 Workflow가 `QUALITY_BELOW_THRESHOLD`로 처리한다.
- 이미지 ID는 Skill이 만들지 않는다. HTML 변환은 URL 스킴·이스케이프 처리를 강화했고, 이미지 변환은 EXIF/GPS를 제거한다(Pillow 미설치로 미검증).
- 설정: 작업별 모델 역할은 `config/model-config.json`, 품질 기준값은 `config/quality-rules.json`에 둔다. 7.5·15장의 YAML 대신 PyYAML 설치 전까지 JSON을 쓴다. 기준값(본문 최소 1500자, 중복 비율, 미확인 비율, SEO 본문 증가 10%)은 실제 품질 테스트 전 임시값이다.
- `run_script.py`로 Script도 표준 봉투로 호출한다.

보류했던 4건은 20.13에서 확정했다. 위 정리는 기존 확정 사항에 맞춘 구현 보완이며 다르게 정하고 싶으면 바꿀 수 있다.

## 20.13 보류 4건 확정

2026-11-12에 사용자가 20.12의 보류 항목을 권장안대로 확정하도록 맡겼다. 다음과 같이 정하고 구현했다(단위 테스트 121개 통과). 바꾸고 싶으면 이 절을 고친다.

1. 토큰 사용량 보고: `llm` 어댑터는 텍스트 또는 `{"text", "usage": {"input_tokens", "output_tokens"}}`를 반환할 수 있다. 모든 응답 봉투에 `usage`(AI·검색 호출 수, 토큰 수, `input_hash`)를 넣는다. 어댑터가 토큰을 보고하지 않으면 `null`로 둔다. 비용(`estimated_cost`)은 가격표가 바뀌므로 n8n이 계산하고 Skill은 가격을 갖지 않는다. `input_hash`는 모듈·입력과 설정 파일 버전으로 만든다. 이유: 9장 Execution Logs의 `token_usage`·`input_hash`를 채우고 월 한도 관리를 가능하게 한다.
2. platform-adaptation 스크립트 우선: blogspot은 SEO 처리된 원고의 H2/H3 구조를 그대로 쓰므로 AI 없이 HTML로 변환한다. 다른 플랫폼 결과물과 너무 비슷하거나 콘텐츠 규칙에 걸리면 AI로 넘어간다. naver는 말투·문단 재작성이 필요해 항상 AI를 쓴다. `adaptation_mode=ai`로 강제할 수 있다. 이유: 두 플랫폼 발행 시 AI 호출이 2회에서 1회로 줄고, naver 결과물이 원고와 달라 중복 문서 방지 규칙도 지켜진다.
3. performance-analysis Publishing 참조: 입력에 `publishing[]`(publishing_id, platform, human_published_at)을 받는다. 플랫폼별 최신 발행 시각 이전 측정값은 제외하고 `days_since_publish`를 붙이며, 발행 후 7일(`early_period_days`, 임시값) 안의 조회수 감소는 감소 제안에서 뺀다. 생략은 허용하되 경고한다. 이유: 발행 시점이 없으면 초기 급등 뒤 자연 감소를 문제로 잘못 판단한다.
4. topic-discovery `locale`: 현재 `ko-KR`만 허용하고 다른 값은 `INVALID_INPUT`으로 막는다. 이유: 한국어 블로그만 운영하며 다른 값을 조용히 무시하면 잘못된 기대를 만든다.

## 20.14 오케스트레이션 기반 확정

2026-11-12에 n8n 연동 전 밑작업으로 오케스트레이션 기준을 [docs/ORCHESTRATION_FOUNDATION.md](docs/ORCHESTRATION_FOUNDATION.md)에 정리했다. 독립 검토에서 나온 지적은 사용자가 맡긴 대로 권장안으로 확정하고 구현했다(단위 테스트 132개 통과, 설치 없음). 바꾸고 싶으면 이 절을 고친다.

1. 재시도 책임 분리: n8n은 `API_TRANSIENT`·`API_RATE_LIMITED`만 자동 재시도한다. JSON 수정(최대 2회)과 품질 재실행(최대 2회)은 모듈 안에서 끝나므로, 모듈이 `INVALID_JSON`·`QUALITY_BELOW_THRESHOLD`를 반환하면 다시 실행하지 않고 `NEEDS_REVISION`으로 보낸다. 이유: 두 곳에서 반복하면 9.2의 한도를 넘는다.
2. 호출 전 `input_hash`: `run_skill.py`·`run_script.py`에 `--hash-only`를 두어 모듈을 실행하지 않고 실제 실행과 같은 `input_hash`를 돌려준다. 같은 함수로 계산하므로 값이 어긋나지 않는다. 이유: 9.3의 중복 실행 방지를 호출 전에 판단해야 하고, n8n에서 해시를 다시 구현하면 조용히 어긋날 수 있다. `id-allocator`는 같은 요청에도 새 ID를 내야 하므로 재사용 대상에서 뺀다.
3. CLI 응답 규칙: 모든 결과를 stdout의 JSON 봉투 하나로 낸다. 종료 코드 0은 `output`, 1은 `error`이며, 모듈을 불러오지 못한 경우도 `UNKNOWN_FAILURE` 봉투로 낸다. 봉투가 없거나 식별자가 다르거나 시간 초과면 n8n이 `UNKNOWN_FAILURE`로 처리하고, stderr 원문은 저장하지 않는다.
4. 날짜 일련번호 발급: 운영 PC가 한 대이므로 `scripts/id-allocator`가 OS 파일 잠금으로 발급을 직렬화한다. 입력은 `kind`(`topic`·`content`), `date`, `count`(1~100), `floor`(Sheets에 이미 있는 최대 번호)이며, 상태는 `state/id-sequences.json` 또는 `BLOG_ID_STATE_DIR`에 둔다. `floor` 아래로 내려가지 않으므로 상태 파일이 사라져도 충돌하지 않는다. 잠금 시간 초과·상태 파일 손상·일련번호 소진은 `STORAGE_FAILURE`이며, 쓰지 못한 번호는 재사용하지 않는다. Skill은 이 Script를 호출하지 않는다.
5. 사실 검증 재작성 횟수: Content Pipeline에 `review_rework_count`를 추가한다. 사실 검증 실패로 `DRAFTING`에 돌아갈 때마다 1씩 올리고, 2회를 넘는 세 번째 실패는 `NEEDS_REVISION`으로 보낸다. `NEEDS_REVISION`에서 재개하거나 원고·발행 거부로 새 작성 주기가 시작되면 0으로 되돌린다. SEO 뒤 재검증도 같은 횟수를 쓴다. 이유: 재작성마다 새 `run_id`라서 `attempt_no`로 셀 수 없다.
6. 워크플로 경계: 주제 발굴·콘텐츠 제작·발행·성과 분석 4개로 나누고, 콘텐츠 제작은 `PUBLISH_READY`에서 끝나며 발행 워크플로가 `WAITING_FOR_PUBLISH_APPROVAL`로 바꾼다. `INTERVIEWING`은 필수 질문 답변을 기다리는 사람 대기 상태로 다룬다. SEO 응답의 `requires_refactcheck=true`는 원고 승인 전 사실 재검증으로 보낸다.

---

# 21. PC에서 작업을 이어갈 때 사용할 지시문

이 문서를 PC의 ChatGPT 또는 Claude에 첨부한 후 다음 지시문으로 시작한다.

---

`Phase_0_design.md`와 `docs/`의 상세 문서를 프로젝트의 현재 기준 설계 문서로 사용해줘.

우리는 Superpowers 개발 방법론을 적용하여 블로그 자동화 시스템을 구축하고 있어.

반드시 다음 원칙을 지켜줘.

1. 기존에 확정된 의사결정을 임의로 변경하지 말 것.
2. 아직 결정되지 않은 사항은 확정된 것처럼 가정하지 말 것.
3. 한 번에 여러 모듈을 개발하지 말 것.
4. Brainstorming부터 순서대로 진행할 것.
5. 설계가 충분히 검토되기 전에는 코드를 작성하지 말 것.
6. 토큰 최적화와 콘텐츠 품질을 동시에 고려할 것.
7. 독립 모듈 개발과 테스트를 완료한 후 통합할 것.
8. 중요한 의사결정은 나에게 하나씩 질문할 것.
9. 각 일정 단계가 끝날 때 관련 Markdown 문서를 생성하거나 수정해 결정 사항과 미확정 사항을 반영할 것.

PHASE 0 설계 문서 패키지는 완료되었어. 현재 환경은 개인 운영 PC가 아니므로 개발 도구를 설치하거나 설정하지 마. 사용자 지시로 10개 Skill·5개 Script의 표준 라이브러리 구현과 단위 테스트가 이미 있어(20.12~20.14). API 호출·자격증명 입력·공급자 연동은 지정된 개인 PC의 환경 검증과 별도 승인 전에는 하지 마.

새 모듈 구현은 사용자 승인 후에만 진행해.

---

**문서 끝**
