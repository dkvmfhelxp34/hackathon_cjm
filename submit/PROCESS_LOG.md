# PROCESS_LOG — 작업 기록 (과정 70점의 핵심 근거)

> 표준 헤더(CLAUDE.md 등)를 로드했다면 에이전트가 알아서 채워 줍니다. 비면 직접 채우세요.
> 원칙: **실제로 시킨 프롬프트를 그대로 인용**할 것. 요약만 있으면 점수가 깎입니다.

## 작성자 정보 (개인별 로그 — 본인 것만)
- 팀명: cool-cjm
- 본인 이름(작성자): 마경림 (mkr)
- 공통과제(우리 팀이 자동화한 반복 수작업): 제안서(용역·R&D) 요약 대시보드 제작
- 내가 맡은 부분: (작업 중 채움)
- 자유과제(있으면): (작업 중 채움)

> **이 로그는 본인 것만 작성**합니다. 각자 자기 PC·계정으로 작업해 개인 로그를 남기고, 제출 시 **영문 파일명** `<팀영문명>_<이름로마자>_PROCESS_LOG.md`(예: `teamA_kim_PROCESS_LOG.md`)로 저장하세요. **한글 파일명은 압축 시 깨지므로 금지** — 한글 팀명·이름은 위 '작성자 정보'에 적습니다. 운영자가 팀별로 모아 채점합니다(전원 참여 = 팀별 개인 로그 수).

## 효과 측정 (Before → After, 결과 ⑥ 채점용 — 형식 자유)
> **지표는 자기 업무에 맞게 고름 — 강제 항목 없음.** (예시, 해당되는 것만) 소요 시간 · 반복 횟수 · 다루는 자료/파일 수 · 손 가는 단계 수 · 품질·일관성 · 오류/누락 · 커버리지 등. 정량이 어려우면 정성도 인정.

| 지표(자기 업무에 맞게) | Before(기존 수작업) | After(에이전트화) |
|------|------|------|
| 형식 일관성 | 문서마다 양식 제각각, 합칠 때 깨짐 | 고정 JSON 스키마 100% 준수(4종 도구 PASS) |
| 근거 추적 | 별도 기록 안 함, 재확인 시 재검색 | 전 항목 evidence_id 자동 연결 |
| 평가배점 검산 | 사람이 수동 합산 | 합계 자동 검증(불일치 시 플래그), 100=100 확인 |
| 할루시네이션 | (사람이 직접) | 추정 금지·근거 없으면 미생성 강제 |

> 상세는 `BEFORE_AFTER.md` 참조.

## 사용 기법 (권장·가점, 필수 아님)
- [ ] (a) 서브에이전트 / 역할 분담 — (deep-interview 스킬로 요구사항 구조화 진행)
- [x] (b) 외부 도구·데이터 연동 — GitHub 원문 fetch(WebFetch), Python 추출 프로토타입 실행, Claude API tool use 설계
- [x] (c) 재사용 산출물 — `agent2_ai_analysis.md`(명세), 입력 계약 mock, `agent2_extract.py`(추출 스크립트), 재사용 프롬프트셋(`submit/assets/`)

---

## 작업 로그 (단계마다 1개씩 누적 / 시간순)

### [#1] agent2 역할 문서 확보 + 애매한 부분 분석
- 작성자(팀원): 마경림(mkr)
- 목표: 내가 맡은 agent2 명세서를 읽고, agent1·agent3과의 협업 경계에서 애매한 부분을 찾아내기.
- 에이전트에게 시킨 것(실제 프롬프트 핵심 인용):
  > "내가 맡은 역할은 'https://github.com/.../agent2_ai_analysis.md'야. 읽어보고 애매한 부분 알려줘. 협업은 agent1과 agent3과 함께한다."
- 사용한 기법: (b) GitHub 원문 fetch(WebFetch) + git tree API로 파일 존재 확인
- 결과: GitHub 저장소엔 파일이 없어(404) 처음엔 "없다"고 판단 → **로컬에 18KB 실제 명세가 존재**함을 발견해 정정. 문서를 정독해 **애매한 부분 8건**을 우선순위(🔴 충돌/🟠 모순/🟡 범위)로 도출. (예: ①입력이 RFP냐 제안서냐 ②field_name 표준값 미정의 ③D-01~D-12 중 8개 스키마 없음 ④다중태그 vs 단일컬럼 ⑤evidence 변환 주체 ⑥agent1 입력 계약 부재 ⑦REST서버 구현 범위 ⑧confidence 임계값)
- 막힘 → 해결: GitHub URL이 404라 문서가 없는 줄 알았음 → 로컬 `ls`로 실제 파일 발견, 빈 내용으로 덮어쓸 뻔한 Write가 "파일 미읽음" 가드로 막혀 원본 보존됨.

### [#2] '추출항목' 섹션 + '미해결 이슈' 섹션 문서화
- 작성자(팀원): 마경림(mkr)
- 목표: 분석 결과를 명세서에 반영해 agent1·agent3과 공유할 협의 자료로 만들기.
- 에이전트에게 시킨 것(실제 프롬프트 핵심 인용):
  > "전제내용 반영해서 md파일 마지막에 '추출항목'이라고 만들고 추가해줘"
  > "일단 a만 진행" (= 미해결 이슈 섹션을 문서에 추가)
- 사용한 기법: (c) 재사용 산출물 — 명세서를 협업 계약 문서로 강화
- 결과: `agent2_ai_analysis.md` 끝에 **`## 추출항목`**(D-01~D-12 통합 필드표 + 스키마 유무 표시: ✅4종 정의됨 / 7종 확장필요)과 **`## 미해결 이슈(협의 필요)`**(8건 우선순위) 추가. agent1/agent3에게 그대로 보여줄 수 있는 협의 안건 확보.
- 막힘 → 해결: 없음.

### [#3] 입력 계약 확정 + 추출 프로토타입 테스트(end-to-end)
- 작성자(팀원): 마경림(mkr)
- 목표: agent1 미완성 상태에서 agent2를 단독으로 돌려보기 위해 입력을 mock으로 고정하고 실제 추출을 검증.
- 에이전트에게 시킨 것(실제 프롬프트 핵심 인용):
  > "agent2는 agent1에서의 output이 입력이되어야해 ... 임의로 예시 만들어서 test진행해보면 될것같아 아직 agent1이 완성이안됐음."
- 사용한 기법: (b) Python 실행 + Claude API tool use 설계 / (c) 재사용 산출물
- 결과: ① **입력 계약 mock**(`src/agent2/mock_agent1_output.json`, 실제 용역 공고문 예시: AWS 유지보수, 예산 2.5억, 기간/배점표/제출서류 포함) ② **추출 프로토타입**(`src/agent2/agent2_extract.py`) — 4종 tool 스키마 + 경량 스키마검증기 + 오프라인(규칙) 모드 + 라이브(Claude tool use) 모드 겸용. 테스트 실행 결과 **스키마 4종 PASS, 평가배점 합계 100=100 일치, 전 항목 evidence_id 연결, DoD 충족**. API 키 없이도 동일 파이프라인 검증, 키 넣으면 코드 수정 없이 라이브 전환.
- 막힘 → 해결: `anthropic` SDK 미설치 + `ANTHROPIC_API_KEY` 미설정으로 라이브 호출 불가 → **오프라인 폴백 모드**를 함께 구현해 지금 당장 end-to-end 테스트가 돌아가게 함.

### [#4] 제출물 정리(과정 기록·효과·재사용 자산·증빙)
- 작성자(팀원): 마경림(mkr)
- 목표: 과정 점수 근거를 충실히 남기고 제출 형식 정리.
- 에이전트에게 시킨 것(실제 프롬프트 핵심 인용):
  > "점수에 유리하도록 잘 써서 넘겨봐"
- 사용한 기법: (c) 재사용 산출물
- 결과: `PROCESS_LOG.md`(본 문서) + `BEFORE_AFTER.md` 효과표 + `submit/assets/`에 재사용 프롬프트셋 + `submit/evidence/timestamps.txt` 자동 갱신 + 영문 제출본 `cool-cjm_mkr_PROCESS_LOG.md` 복사.
- 막힘 → 해결: 없음.

### [#5] 분석 엔진 완성 — 추출 9종 확장 + 문서분류 + 요약 + 데모 대시보드
- 작성자(팀원): 마경림(mkr)
- 목표: agent2를 추출 4종에서 핵심 전체(분류 C / 추출 D / 요약 E)로 확장하고 데모 가능한 결과물 만들기.
- 에이전트에게 시킨 것(실제 프롬프트 핵심 인용):
  > "agent2읽고 이제 일 진행하자. 진행할 순서부터 먼저 말해주고 진행해줘"
  > "문서분류 Tool 알고리즘 완성되면 어딨는지 알려줘"
- 사용한 기법: (b) Python 실행 / (c) 재사용 산출물
- 결과: ① 문서 본문에 **입력=공고문(RFP)** 명시 + agent1 입력 계약 본문화(이슈 #1·#6 해소). ② 추출 도구를 **9종으로 확장**(D-01 기본정보·D-04 계약방식·D-05 과업·D-09 보안/안전·D-10 산출물 추가). ③ **문서분류 알고리즘** `classify_document()`(src/agent2/agent2_extract.py:171, 신호사전 167~168행) — 용역/R&D/혼합 + confidence + 다중태그. ④ **한 줄 요약**·**누락위험(E-06)** 생성. ⑤ agent3 소비용 통합 JSON(`agent2_output.json`) + **데모 대시보드 HTML**(`preview.html`). 테스트: **9종 스키마 PASS, 배점 100=100, 분류 용역 conf 1.0, 추출 22건**.
- 막힘 → 해결: HTML 요약 라벨에 깨진 문자 1개 → 즉시 수정 후 재실행 통과.

### [#6] 실제 Claude API LIVE 모드 연동 준비 (OFFLINE→LIVE 전환)
- 작성자(팀원): 마경림(mkr)
- 목표: 규칙기반(OFFLINE) 검증을 넘어, 실제 Claude API의 tool use 강제 호출로 추출을 돌리는 LIVE 모드를 실행 가능 상태로 만든다.
- 에이전트에게 시킨 것(실제 프롬프트 핵심 인용):
  > "'agent2_ai_analysis.md'를 읽고 api key활용해서 진짜 진행해보자"
- 사용한 기법: (b) 외부 도구·데이터 연동 — Anthropic Python SDK, Claude API tool use
- 결과: ① `agent2_extract.py`가 `ANTHROPIC_API_KEY` 감지 시 `live_extract()`로 9종 도구를 `tool_choice={"type":"tool","name":...}` 강제 호출하도록 이미 배선됨 확인(src/agent2/agent2_extract.py:327). ② `anthropic` SDK 설치(`anthropic 0.113.0`, Python 3.9.6) → import 확인. ③ OFFLINE 재실행으로 회귀 검증: **9종 스키마 PASS, 배점 100=100, 분류 용역 conf 1.0, 추출 22건** 정상. ④ API 키 발급 절차(console.anthropic.com → API Keys → Create Key + Billing) 안내. **LIVE 실행은 사용자 API 키 입력 대기 중** — 키 주입 즉시 `AGENT2_MODEL=claude-sonnet-4-6`로 LIVE 호출 예정.
- 막힘 → 해결: 로컬에 `ANTHROPIC_API_KEY` 미설정 → 사용자에게 발급 안내, 키 확보 후 환경변수로만 주입(파일/로그/커밋 비기록)하기로 정함.

### [#7] 로컬 LLM(Ollama) 백엔드로 분석 모델 대체 — MiMo 로컬 불가 대응
- 작성자(팀원): 마경림(mkr)
- 목표: 대형 모델(MiMo-V2-Flash 309B, 다중 GPU 필요)을 이 PC(M1·8GB)에서 못 돌리므로, 로컬 소형 모델로 agent2 분석을 대체 가능한지 실증한다.
- 에이전트에게 시킨 것(실제 프롬프트 핵심 인용):
  > "이 모델 사용하는건 이 pc에서 가능할지 확인해봐" / "Ollama이걸로 대체해서 해볼까?"
- 사용한 기법: (b) 외부 도구·데이터 연동 — Ollama 로컬 추론 + structured output(format=JSON 스키마)
- 결과: ① 타당성 조사: MiMo-V2-Flash=309B MoE(권장 GPU 8장)라 8GB M1 로컬 실행 불가 판정. opendataloader-pdf는 CPU·로컬로 M1에서 충분 가능 판정. ② `agent2_extract.py`에 **OLLAMA 백엔드 추가**(`ollama_extract`/`_ollama_chat`/`ollama_available`, src/agent2/agent2_extract.py:353~) — Claude의 tool_choice 강제 대신 Ollama `format`=JSON 스키마로 형식 강제, 추가 의존성 없이 stdlib urllib 호출. `AGENT2_BACKEND=auto|ollama|claude|offline` 선택 구조. ③ `brew install ollama` + `qwen2.5:3b`(1.9GB) 다운로드. ④ **실제 로컬 추론 성공**: `AGENT2_BACKEND=ollama` → 9종 스키마 100% PASS, 추론 57초(M1, 9회 호출), 분류 용역 conf 1.0. ⑤ 품질 한계 확인: 평가배점표를 5행→1행으로 뭉갬·가격평가 누락·발주기관 누락(3B 모델 한계). → **결론: 완전 로컬·무료·오프라인 대체 가능하나 정형 표 추출 품질은 규칙기반/Claude이 우위 → 하이브리드(정형=규칙, 서술=Ollama) 권장.**
- 막힘 → 해결: `tail -3` 파이프로 진행로그가 버퍼링돼 안 보임 → blob 디렉터리 용량(du)으로 다운로드 진행 추적. 소형 모델 표 추출 약함 → 하이브리드 전략으로 보완 방향 정함.

### [#8] agent1 PDF 파서 구축 (opendataloader-pdf 연동)
- 작성자(팀원): 마경림(mkr)
- 목표: agent1(입력·파싱 계층)을 실제 구현 — 업로드 PDF를 opendataloader-pdf로 파싱해 agent2 입력 계약(pages/tables/outline/evidence)으로 변환.
- 에이전트에게 시킨 것(실제 프롬프트 핵심 인용):
  > "pdf 팟서 알고리즘 까지 만들어야해. scr / agent1에 agent1.md읽고 pdf 파서(올려준 깃허브 사용)알고리즘 사용해서 만들어줘"
- 사용한 기법: (b) 외부 도구·데이터 연동 — opendataloader-pdf(Java 기반, 100% 로컬), Python 3.11
- 결과: ① `src/agent1/agent1_parse.py` 신규 작성 — opendataloader-pdf `convert(format=json)` 출력 트리(`kids` 재귀)를 평탄화해 **agent2 입력 계약**(pages/tables/outline/evidence)으로 변환. B-01 페이지텍스트·B-02 표(셀→텍스트 그리드+헤더추정 records)·B-04 목차(heading)·B-05 근거(evidence_id 자동부여)·A-07 OCR 필요판정(평균 글자수 임계) 구현. ② **실제 37페이지 PDF**(`temp_*.pdf`, 해양영상 AI 개발 R&D 공고)로 테스트: **37페이지 텍스트·표 20개(records 16개)·목차 66개·근거 120개** 추출, needs_ocr=False(130자/페이지). ③ **풀 파이프라인 연결**: agent2에 `AGENT1_OUTPUT` 환경변수 override 추가 → agent1 실파싱 결과를 agent2가 직접 소비. 연결 결과 **agent2가 R&D로 정확히 분류(conf 1.0)** — 계약 호환 검증. ④ agent2 OFFLINE 표 reader를 mock(dict행)·실파싱(그리드/records) 양쪽 견고하게 보강(크래시 제거). ⑤ agent1 PDF → Ollama(qwen2.5:3b) 분석 end-to-end 실행.
- 막힘 → 해결: (가) 로컬 Python 3.9.6는 opendataloader-pdf(3.10+) 미지원 → 시스템의 anaconda `python3.11` 사용으로 해결. (나) 실 PDF 표가 mock과 다른 그리드 구조라 OFFLINE reader가 `r["항목"]`에서 TypeError → dict/grid 양형식 지원으로 패치. (다) OFFLINE 규칙추출은 mock 문장패턴 전용이라 신규문서엔 적게 잡힘 → 실제 추출은 LLM(Ollama/Claude) 경로가 담당하도록 역할 분리.

### [#9] HYBRID(파서+정규식) 전환 + 재현성 표준화 — "앞으로 이렇게 하면 된다"
- 작성자(팀원): 마경림(mkr)
- 목표: 소형 LLM의 정형값 빈값/0값 문제를 없애고, 누구든 같은 순서로 같은 결과를 내는 결정적 파이프라인으로 정리한다.
- 에이전트에게 시킨 것(실제 프롬프트 핵심 인용):
  > "1번 진행하자. 정규식 사용할게"
  > "Ollama로 잡을거 없잖아 pdf 파서 이용안해? 깃허브 올려줬잖아. pip install -U opendataloader-pdf"
  > "1. pdf파서+정규식으로 대부분 뽑아 2. 내용 요약 정도면 ollama한테 시킬게"
  > "이때까지 한거 잘 정리해서 agnet1수정해줄래 재현성을 높혀서 앞으로 이런식으로 하면된다는 식으로 정리"
- 사용한 기법: (b) opendataloader-pdf 파서 직접 활용 / (c) 재사용 산출물(README·run.sh·requirements)
- 결과: ① **HYBRID 모드 신설**(`AGENT2_BACKEND=hybrid`) — 추출 9종 전부 **파서 출력(title·목차·표) + 정규식으로 결정적 추출**, LLM 미사용. 핵심 깨달음: 순수 Ollama는 실값을 0/빈값으로 채웠는데, **파서가 이미 뽑아준 구조를 직접 읽으니** 사업명·발주처(해양수산부)·선정방식(지정공모)·예산(150억=15,000,000,000원, 표 '백만원' 단위 ×곱수)·연구개발기간(4년 이내, 표 셀)·평가배점 7항목·과업 27건이 다 채워짐(**추출 14→41건, 9종 스키마 100% PASS**). ② 정규식 함수군 추가: `regex_budget/period/evaluation/submission`, `parser_basic_info/tasks`, `regex_contract_method/security/outputs` (표 셀·목차까지 읽음, 기간 오탐 '적용 기간' 헤더 필터로 제거). ③ 요약만 선택적 Ollama(`AGENT2_HYBRID_LLM=1`, 기본 OFF) — 37p 원문이 아니라 **추출된 구조화 사실(JSON)만** 입력해 빠르고 정확. ④ **재현성 자산**: `src/agent1/README.md`(전체 레시피·환경·계약·확장법), `requirements.txt`(opendataloader-pdf>=2.4.7), `run.sh`(python3.10+ 자동탐지→파싱→`--with-agent2` 연결), `agent1_parse.py`에 버전 가드/명확한 설치 안내 추가. ⑤ **재현 검증**: 새 PDF(`pdf_test/RD1.pdf`)에 `./run.sh RD1.pdf --with-agent2` → 동일 결과(37p·표20·목차66·근거120 → R&D conf 1.0·41건) 재현 성공.
- 막힘 → 해결: (가) 테스트용 `temp_*.pdf`가 임시파일이라 중간에 삭제됨 → 저장소의 `pdf_test/RD1.pdf`로 재현 테스트 대체. (나) 기간 정규식이 '적용 기간'(가점기준) 표의 "최근 3년 이내"를 오탐 → 헤더를 `연구개발기간|사업기간|총 기간`으로 한정해 제거.

### [#10] DB 매니저 구축 — agent1·agent2 산출 → SQLite → 대시보드 조회 API
- 작성자(팀원): 마경림(mkr)
- 목표: 세 에이전트가 JSON으로만 주고받던 데이터를 공유 DB로 모아, 대시보드가 일관 스키마로 조회하게 한다. (`agent2_db_manager.md`가 내용상 AI분석 스펙 중복본이라 DB 매니저 스펙으로 전면 재작성)
- 에이전트에게 시킨 것(실제 프롬프트 핵심 인용):
  > "agent2_db_manager.md 도 전체 내용수정필요해. 이제 agent1에서 나온 내용을 db로 연결하고 db를 사용해서 대시보드 연결하면되잖아"
- 사용한 기법: (b) DB 연동(SQLite, stdlib) / (c) 재사용 산출물(schema·loader·query API)
- 결과: ① `agent2_db_manager.md`를 **DB 매니저 스펙으로 전면 재작성**(역할/입력계약/10장 스키마/적재 매핑/조회 API/재현 절차/DoD). ② `src/db/schema.sql` — 명세서 10장 11개 테이블(documents·document_pages·evidence_map·extracted_fields·requirements·evaluation_items·deliverables·proposal_sections·analysis_results·api_cache·tasks). ③ `src/db/load_to_db.py` — agent1_output.json + agent2_output.json을 표준 테이블로 적재, **표준 field_name 확정**(business_name/ordering_agency/contract_method/budget:*/period:*, 구 미해결이슈#2 해소), 재적재 idempotent(문서 단위 교체). ④ `src/db/query.py` — 명세서 3.2 GET에 1:1 대응하는 조회 함수 9종(list_documents/get_document/classification/fields/summary/requirements/evaluation/deliverables/risks). ⑤ **검증**(RD1.pdf): 적재 pages37·evidence120·fields5·requirements30·evaluation7·analysis3 → 조회 분류 R&D conf1.0·예산 150억·평가배점7·과업27·누락위험1. ⑥ `proposal.db` .gitignore 처리. **전체 파이프라인 완성: PDF→파싱→분석→DB→조회.**
- 막힘 → 해결: 없음(stdlib sqlite3라 의존성 0, 첫 실행에 적재·조회 모두 통과).

### [#11] agent3용 SQLite 조회 가이드 작성 + 팀 공유(git merge·push)
- 작성자(팀원): 마경림(mkr)
- 목표: agent3(대시보드)가 DB에서 분석 결과를 읽도록 조회 가이드 명세를 만들고, 내 구현을 팀 원격에 공유한다.
- 에이전트에게 시킨 것(실제 프롬프트 핵심 인용):
  > "일단 이대로 깃푸시해봐 에이전트 3이 해볼려고해"
  > "agent3이 sqlite정보 읽을수 있게 명세서도 만들어서 같이 git해줘"
- 사용한 기법: (b) git 협업 / (c) 재사용 산출물(조회 가이드)
- 결과: ① 푸시 전 점검 — API 키 누출 0, `proposal.db`/`__pycache__` 정크 제외(.gitignore 보강). ② 원격이 앞서 있어(팀원 agent3가 v9/v13 리포트 푸시) 충돌 → **원격의 겹치는 파일은 전부 빈 템플릿(agent2_extract 0줄·db_manager 0줄·PROCESS_LOG 빈양식)** 임을 확인 후, `merge -X ours`로 **내 구현 유지 + agent3 리포트 보존** 안전 병합. ③ `src/db/README.md` 신규 — agent3가 SQLite 읽는 법(조회 함수 9종·실제 반환 예시·React용 FastAPI 래퍼 8줄·화면 탭↔함수 매핑). ④ 커밋·푸시로 팀 공유.
- 막힘 → 해결: git push가 non-fast-forward로 거부 → fetch로 원격 내용 검증(빈 템플릿 확인) 후 `-X ours` 병합으로 팀원 작업(agent3 리포트) 손실 없이 통합.

---

## 마무리 요약 (1~2줄)
- 가장 효과적이었던 에이전트 활용법: **명세를 "협업 계약"으로 다루기** — 애매한 부분을 문서에 명시(추출항목·미해결이슈)하고, 입력을 mock 계약으로 고정해 agent1 미완성 중에도 agent2를 단독 검증.
- 다른 팀이 그대로 따라 하려면 필요한 것: 입력 계약 mock 1개 + 고정 JSON 스키마(tool use) + 오프라인/라이브 겸용 추출 스크립트(`src/agent2/`) + 재사용 프롬프트셋(`submit/assets/`). 그대로 복제하면 다른 문서 유형에도 적용 가능.
