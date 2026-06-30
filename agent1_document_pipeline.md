# 에이전트 1 작업 명세 - 문서 처리 파이프라인 및 저장소

## 0. 에이전트 역할

이 에이전트는 시스템의 입력 계층과 저장 계층을 담당한다. 사용자가 업로드한 원본 문서를 분석 가능한 형태(텍스트, 표, 페이지 이미지)로 변환하고, 모든 추출 결과와 Claude API 분석 결과를 저장하는 데이터베이스를 소유한다.

핵심 책임은 다음 네 가지다.

1. 다양한 형식(HWPX, HWP, PDF)의 문서를 안정적으로 변환한다.
2. 변환된 문서에서 페이지별 텍스트, 표, 목차, 페이지 이미지를 추출한다.
3. 추출 결과를 원문 근거(페이지, 문장, 좌표)와 함께 DB에 저장한다.
4. 에이전트 2의 Claude API 호출을 지원하도록 DB와 시크릿(API 키)을 구성한다.

근거: 원본 명세서 7장(문서 업로드/변환/파서/OCR/데이터 저장소 모듈), 8.1, 8.2, 10장.

## 1. 명세서 작업 매핑

| 명세서 작업 ID | 작업명 | 비고 |
|---|---|---|
| A-01 | 파일 업로드 | HWPX, HWP, PDF, ZIP 지원 |
| A-02 | 파일 형식 판별 | 확장자 + MIME 타입 |
| A-03 | HWPX 파싱 | ZIP/XML 구조 텍스트 추출 (MVP 필수) |
| A-04 | HWP 변환 | MVP에서는 제외 또는 옵션 (명세서 11장 기준) |
| A-05 | PDF 정규화 | 페이지 수, 암호화, 텍스트 포함 여부 확인 |
| A-06 | 이미지 렌더링 | 페이지 → PNG |
| A-07 | 변환 검증 | OCR 필요 여부 판정 포함 |
| B-01 | PDF 텍스트 추출 | page_text 저장 |
| B-02 | 표 추출 | table_json |
| B-03 | OCR 처리 | MVP에서는 선택 (명세서 11장) |
| B-04 | 목차 추출 | document_outline |
| B-05 | 페이지 근거 저장 | evidence_map |
| B-06 | 중복 제거 | 머리말/꼬리말/중복 표 제거 |

추가로 이 에이전트는 10장 데이터베이스 전체 스키마의 정의/마이그레이션과, Claude API 사용을 위한 저장소 구성을 소유한다(4절, 5절).

## 2. 입력 (의존성)

- 외부 입력: 사용자가 업로드한 원본 파일(HWPX/HWP/PDF/ZIP). 다른 에이전트에 대한 의존성 없음.
- 파이프라인 시작점이므로 다른 에이전트의 산출물을 기다리지 않고 독립 개발 가능하다.

## 3. 출력 (다른 에이전트에 제공하는 계약)

에이전트 2와 3이 이 데이터를 소비한다. DB 테이블과 REST API 두 형태로 제공한다.

### 3.1 제공 API (문서 수집/조회)

| 메서드 | 엔드포인트 | 설명 |
|---|---|---|
| POST | /api/documents/upload | 파일 업로드, document_id 반환 |
| GET | /api/documents/{id} | 문서 메타데이터 조회 (status 포함) |
| GET | /api/documents/{id}/pages | 페이지별 텍스트/이미지 경로 조회 |
| GET | /api/documents/{id}/tables | 추출된 표(table_json) 조회 |
| GET | /api/documents/{id}/outline | 목차 트리 조회 |
| GET | /api/documents/{id}/evidence | evidence_map 조회 |
| GET | /api/documents/{id}/page-image/{no} | 페이지 PNG 반환 |

### 3.2 status 값 정의 (에이전트 3 상태 표시와 공유)

`uploaded` → `converting` → `extracting` → `extracted` → (에이전트 2가 이후 단계로 전환)

오류 시 `error`. 에이전트 2는 `extracted` 상태를 트리거로 분석을 시작한다.

## 4. 데이터베이스 스키마 (이 에이전트가 소유)

명세서 10장 기준. 세 에이전트가 공유하는 단일 스키마이므로 이 에이전트가 정의/마이그레이션을 관리하고, 에이전트 2·3은 합의된 테이블에만 쓰기를 한다. MVP는 SQLite, 확장 시 PostgreSQL을 가정한다.

### 4.1 테이블별 쓰기 주체

| 테이블 | 쓰기 주체 |
|---|---|
| documents, document_pages, evidence_map | 에이전트 1 |
| extracted_fields, requirements, evaluation_items, deliverables, proposal_sections, analysis_results, api_cache | 에이전트 2 |
| tasks | 에이전트 3 |

documents.document_type는 에이전트 1이 업로드 시 null로 두고, 에이전트 2가 분류 후 갱신한다.

### 4.2 Claude API 사용을 위한 스키마 조정

에이전트 2가 Claude API(tool use 포함)를 호출한 결과와 비용/캐싱 정보를 저장할 수 있도록 다음을 추가/확장한다. 핵심 목적은 명세서 13장의 "API 비용" 리스크 대응(chunking + 캐싱 + 결과 저장)이다.

analysis_results 테이블 확장:

| 컬럼 | 타입 | 설명 |
|---|---|---|
| result_id | PK | |
| document_id | FK | |
| analysis_type | text | summary/classification/requirements 등 |
| result_json | json/text | Claude tool use가 반환한 구조화 결과 |
| model_name | text | 예: claude-opus-4-8, claude-sonnet-4-6 |
| input_tokens | int | 호출 입력 토큰 수 |
| output_tokens | int | 호출 출력 토큰 수 |
| stop_reason | text | end_turn / tool_use 등 |
| created_at | datetime | |

api_cache 테이블 신설(중복 호출 방지로 비용 절감):

| 컬럼 | 타입 | 설명 |
|---|---|---|
| cache_id | PK | |
| document_id | FK | |
| request_hash | text | 모델명 + 프롬프트 + 도구정의 + 입력청크의 해시 |
| response_json | json/text | 캐시된 응답 |
| model_name | text | |
| created_at | datetime | |

조회 키는 request_hash이며, 동일 해시가 있으면 Claude API를 다시 호출하지 않고 캐시를 반환한다. 페이지 단위 chunking 결과를 캐싱하여 긴 문서의 재호출 비용을 줄인다.

### 4.3 API 키 보안 처리 (중요)

Claude API 키는 DB에 평문 저장하지 않는다. 키 자체는 환경변수 또는 시크릿 매니저로 주입하고, DB에는 키를 참조하지 않는다.

- API 키: 환경변수 `ANTHROPIC_API_KEY`로 주입. 코드/DB/로그에 노출 금지.
- 설정 메타(사용 모델명, 토큰 한도, 캐시 정책 등)만 config 테이블 또는 설정 파일에 저장.
- 키가 필요한 호출(에이전트 2)은 런타임에 환경변수에서 읽어 사용한다.

근거: 명세서 13장 "보안 문제"(파일 암호화, 접근권한, 로그관리) 및 일반 시크릿 관리 원칙. 키를 DB에 넣지 않는 이유는 DB 유출 시 키까지 노출되기 때문이다.

## 5. 상세 작업 체크리스트

### 5.1 업로드/변환

- [ ] 파일 업로드 엔드포인트 구현, 원본 파일 저장 (A-01)
- [ ] 확장자 + MIME 타입으로 형식 판별 (A-02)
- [ ] HWPX를 ZIP으로 해제 후 내부 XML에서 본문 텍스트 추출 (A-03)
- [ ] HWP 변환은 MVP에서 옵션 처리. 변환기 연동 인터페이스만 정의 (A-04)
- [ ] PDF 페이지 수, 암호화 여부, 텍스트 레이어 존재 여부 확인 (A-05)
- [ ] 각 PDF 페이지를 PNG로 렌더링하여 image_path 저장 (A-06)
- [ ] 텍스트 추출량 기준 OCR 필요 여부 자동 판정 후 로그 기록 (A-07)

### 5.2 추출

- [ ] 페이지별 본문 텍스트 추출 후 document_pages 저장 (B-01)
- [ ] 표 구조 추출 후 JSON 저장 (B-02)
- [ ] OCR 처리(선택), confidence 기록 (B-03)
- [ ] 장·절·항 목차 자동 감지 후 트리 저장 (B-04)
- [ ] 추출 항목별 페이지/문장/좌표를 evidence_map에 저장 (B-05)
- [ ] 머리말/꼬리말/중복 제거 후 cleaned_text 생성 (B-06)

### 5.3 저장소/API 키 구성

- [ ] 10장 전체 스키마 마이그레이션 작성
- [ ] analysis_results에 토큰/모델/stop_reason 컬럼 추가
- [ ] api_cache 테이블 및 request_hash 조회 로직 제공
- [ ] ANTHROPIC_API_KEY 환경변수 주입 구조 마련, DB/로그 비노출 보장

## 6. 기술 스택 제안

명세서에 명시된 도구 외에는 검토 대상으로 제안하며 확정은 구현 시 판단한다.

- HWPX: ZIP/XML 직접 파싱
- HWP: 명세서 A-04의 hwp5txt, LibreOffice, Hancom 변환기 중 서버 환경에 맞게 선택 (근거: 명세서 142행)
- PDF 텍스트/표: PDF 파싱 + 표 추출 라이브러리 (구체 라이브러리 성능 수치는 근거자료없음, 구현 시 벤치마크)
- DB: MVP는 SQLite, 확장 시 PostgreSQL (JSON 컬럼 지원으로 result_json/table_json 수용)

## 7. 완료 기준 (Definition of Done)

- HWPX와 PDF 업로드 시 페이지별 텍스트가 document_pages에 저장된다.
- PDF 각 페이지 PNG가 생성되고 image_path로 조회된다.
- 표가 table_json으로 추출되어 API로 조회된다.
- 모든 추출 항목이 evidence_map의 page_no와 연결된다.
- analysis_results와 api_cache가 생성되어 에이전트 2가 토큰/캐시를 기록할 수 있다.
- ANTHROPIC_API_KEY가 환경변수로만 주입되고 DB/로그에 남지 않는다.
- 3.1 API가 정상 응답하고 status 전이가 정의대로 동작한다.

## 8. 주의사항

- HWP는 HWPX보다 변환 난도가 높으므로 MVP에서는 HWPX/PDF를 우선한다 (명세서 13장).
- evidence_map 저장은 후속 에이전트 근거 연결의 전제이므로 누락 없이 구현한다 (명세서 15장 핵심).
- api_cache의 request_hash에는 모델명과 도구정의까지 포함해야 도구가 바뀌었을 때 잘못된 캐시를 반환하지 않는다.
- API 키는 어떤 경우에도 DB·소스·로그·에러 메시지에 출력하지 않는다.
