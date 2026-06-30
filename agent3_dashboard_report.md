# 에이전트 3 작업 명세 - 대시보드 UI 및 리포트 생성 (React)

## 0. 에이전트 역할

이 에이전트는 시스템의 표현 계층을 담당한다. 에이전트 1과 2가 만든 데이터를 React 기반 웹 대시보드로 보여주고, 사용자가 작업 상태를 관리하며, 결과를 PDF/Excel 리포트로 내보내게 한다.

핵심 책임은 다음 네 가지다.

1. 문서 목록, 상세 요약, 작성항목 분류, 체크리스트, 평가 대응 화면을 React로 구성한다.
2. 사용자가 요구사항별 진행 상태와 담당자를 관리하게 한다(tasks 테이블).
3. 1페이지 요약, 상세 요약, 체크리스트, 대응표를 PDF/Excel로 출력한다.
4. 지정된 디자인 리소스와 UI 스킬을 활용해 일관되고 완성도 높은 인터페이스를 만든다.

근거: 원본 명세서 6장(대시보드 목표), 9.1~9.6(화면 명세), 14장.

## 1. 기술 스택 (확정)

- 프레임워크: React (TypeScript)
- 스타일: Tailwind CSS
- 컴포넌트 기반: shadcn/ui + Radix UI 프리미티브
- 모션: 필요한 경우 prefers-reduced-motion 준수 전제로 적용

근거: 사용자 지정(React 기반). shadcn/Radix는 아래 21st.dev 컴포넌트가 이 위에서 동작하기 때문이다.

## 2. 디자인 및 컴포넌트 리소스 (필수 활용)

빌드 전에 아래 리소스를 먼저 적용한다. 디자인 컨텍스트를 코드 작성 전에 확보하는 것이 목적이다.

### 2.1 디자인 시스템 - refero.design DESIGN.md

- 출처: https://styles.refero.design/
- 사용법: 만들 화면(개발자용 데이터 대시보드) 성격에 맞는 스타일을 골라 그 DESIGN.md를 프로젝트 컨텍스트로 가져온다. DESIGN.md는 색상, 타이포그래피, 간격, 컴포넌트 규칙, 모션을 담은 마크다운 디자인 시스템이다.
- 적용 시점: UI 코드를 쓰기 전에 DESIGN.md를 먼저 확보해 첫 초안부터 팔레트/타입스케일/간격 규칙을 따르게 한다. 사후 정리용으로 쓰지 않는다.
- 선택 기준: 입찰/R&D 문서 분석 도구이므로 정보 밀도가 높고 가독성 중심인 SaaS/devtools 대시보드 계열 스타일을 고른다. (refero MCP 또는 refero skill을 쓸 수 있으면 활용)

### 2.2 컴포넌트 - 21st.dev 커뮤니티 컴포넌트

- 출처: https://21st.dev/community/components
- 성격: shadcn/ui 기반 React + Tailwind + Radix 컴포넌트 레지스트리.
- 설치: 필요한 컴포넌트를 `npx shadcn@latest add "https://21st.dev/r/{author}/{component}"` 형태로 설치한다.
- 사용 원칙: 공통 요소(카드, 테이블, 탭, 다이얼로그, 필터, 검색바, 배지, 토스트, 트리뷰, 파일 뷰어 등)는 직접 짜지 말고 이 레지스트리에서 가져와 조정한다.

### 2.3 UI 스킬 - ui-skills

- 출처: https://www.ui-skills.com/ , https://github.com/ibelick/ui-skills
- 설치/탐색 명령:
  - `npx ui-skills start` : 시작 및 라우팅
  - `npx ui-skills categories` : 카테고리 보기
  - `npx ui-skills list --category motion` : 카테고리별 스킬 목록
  - `npx ui-skills get {slug}` : 특정 스킬 내용 확인
  - `npx ui-skills add {slug}` : 스킬 설치
- 권장 스킬(과업 성격에 맞는 최소 집합):
  - baseline-ui : 간격/위계/타이포/레이아웃 정리(deslop)
  - fixing-accessibility : 폼/다이얼로그/키보드 내비/대비 등 접근성 (체크리스트 편집, 필터 폼이 많아 필수)
  - fixing-motion-performance : 다이얼로그/전환 모션 성능 (예: 상세 모달, 탭 전환)
  - interaction-design : 로딩/스켈레톤/토스트 등 마이크로 인터랙션
- 적용 순서: 화면 코드를 작성한 뒤 baseline-ui → fixing-accessibility → fixing-motion-performance 순으로 폴리시 패스를 돌린다. 스킬은 한 번에 1개, 넓은 리뷰일 때만 최대 3개까지 사용한다(ui-skills 루트 권장).

## 3. 입력 (의존성)

에이전트 1과 2의 API를 모두 소비한다.

에이전트 1:
- GET /api/documents/{id} (메타데이터, status)
- GET /api/documents/{id}/pages, /outline, /page-image/{no}
- GET /api/documents/{id}/evidence

에이전트 2:
- GET /api/analysis/{id}/classification, /fields, /summary, /requirements, /proposal-sections, /evaluation, /risks

병렬 개발을 위해, 두 에이전트 API 완성 전에는 각 응답 스키마 기준 mock 데이터로 UI를 먼저 구현한다.

## 4. 출력 (이 에이전트가 소유하는 것)

### 4.1 쓰기 담당 테이블 (명세서 10장)

- tasks (task_id, document_id, assignee, status, due_date)

체크리스트의 반영 여부/담당자/비고는 tasks로 저장한다(requirements 자체는 에이전트 2 소유).

### 4.2 제공 API

| 메서드 | 엔드포인트 | 설명 |
|---|---|---|
| GET | /api/tasks?document_id= | 문서별 작업 상태 |
| POST | /api/tasks | 담당자/상태/마감 지정 |
| PATCH | /api/tasks/{id} | 진행 상태 갱신 |
| GET | /api/reports/{id}/{type} | 리포트 생성/다운로드 |

## 5. 화면별 상세 작업 체크리스트

값(상태, 탭, 분류)은 에이전트 1·2와 합의된 값을 그대로 사용한다. 자체 정의 금지.

### 5.1 문서 목록 (9.1)

- [ ] 문서 카드: 파일명, 문서유형, 발주기관, 예산, 마감일 (21st.dev 카드 컴포넌트 기반)
- [ ] 상태 표시: uploaded/converting/extracting/extracted/error (에이전트 1 status와 일치, 배지 컴포넌트)
- [ ] 필터: 용역, R&D, 공고문, 제안요청서, 마감 임박
- [ ] 검색: 사업명, 발주기관, 키워드
- [ ] 버튼: 상세보기, 요약 다운로드, 체크리스트 다운로드

### 5.2 문서 상세 요약 (9.2)

- [ ] 기본정보: 사업명, 발주기관, 기간, 예산, 계약/선정 방식
- [ ] 핵심 요약: 5줄 요약, 주요 과업, 핵심 리스크
- [ ] 원문 근거: 페이지 번호, 원문 문장, 하이라이트 (evidence 활용)
- [ ] 문서 구조: 목차 트리 (트리뷰 컴포넌트)
- [ ] 원본 뷰어: PDF 페이지 뷰어 (page-image API)

### 5.3 작성항목 분류 (9.3)

- [ ] 탭: 공통/용역/R&D/누락 위험 (section_type: common/service/rnd/missing 매핑, Radix Tabs)
- [ ] 누락 위험 탭은 원문에서 놓치기 쉬운 항목 강조

### 5.4 요구사항 체크리스트 (9.4)

- [ ] 컬럼: 요구사항 ID, 원문 위치, 내용, 분류, 중요도, 반영 여부, 담당자, 비고 (테이블 컴포넌트)
- [ ] 반영 여부(미작성/작성중/완료), 담당자, 비고 편집 가능 (tasks 저장)

### 5.5 평가 대응 대시보드 (9.5)

- [ ] 평가항목별 배점 표시
- [ ] 대응 상태(문단 작성 여부)
- [ ] 근거 요구 여부(실적/증빙/정량지표)
- [ ] 위험도: 배점 높으나 대응 약한 항목 강조

### 5.6 리포트 출력 (9.6)

- [ ] 1페이지 요약보고서 PDF
- [ ] 상세 요약보고서 PDF/DOCX
- [ ] 제안서 작성 체크리스트 Excel
- [ ] 요구사항-제안서 대응표 Excel
- [ ] 용역/R&D 비교표 PDF/Excel
- [ ] 원문 근거 포함 요약 PDF

### 5.7 관리자 기능 (14장)

- [ ] 사용자 관리
- [ ] 문서 관리
- [ ] 분석상태 관리

## 6. 빌드 워크플로 (권장 순서)

1. React + TypeScript + Tailwind + shadcn/ui 초기화
2. refero.design에서 대시보드 성격에 맞는 DESIGN.md를 골라 프로젝트 컨텍스트로 추가 (코드 작성 전)
3. 화면별로 21st.dev 컴포넌트를 설치해 골격 구성 (mock 데이터로 시작)
4. 에이전트 1·2 API 연동으로 mock을 실데이터로 교체
5. `npx ui-skills start` 후 baseline-ui → fixing-accessibility → fixing-motion-performance 폴리시 패스
6. 리포트(PDF/Excel) 출력 연결

## 7. 완료 기준 (Definition of Done)

- React 앱에서 9.1~9.6 화면이 모두 동작한다.
- DESIGN.md 기반 팔레트/타입/간격이 일관되게 적용된다.
- 21st.dev 기반 공통 컴포넌트로 카드/테이블/탭/다이얼로그가 구성된다.
- 상태/탭/분류 값이 에이전트 1·2와 100% 일치한다.
- 체크리스트 편집이 tasks에 저장된다.
- ui-skills 폴리시 패스 후 접근성(키보드/포커스/대비)과 모션 성능 기준을 통과한다.
- prefers-reduced-motion을 준수한다.
- 9.6의 6종 리포트가 정상 생성/다운로드된다.

## 8. 주의사항

- 상태(status), 작성항목 탭(section_type), 요구사항 분류(req_type)는 공유 계약 값을 그대로 사용한다.
- 모든 요약/판단 화면에 원문 근거를 함께 노출한다 (명세서 15장 핵심 4번).
- MVP(명세서 11장)에서 원문 좌표 기반 하이라이트와 다중 문서 비교는 2차 개발이므로, 1차는 페이지 단위 근거 표시까지만 구현한다.
- 디자인 리소스는 참고 기반이며, 특정 컴포넌트/스타일의 성능 수치는 근거자료없음. 적용 후 ui-skills로 검증한다.
