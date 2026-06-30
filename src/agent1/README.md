# agent1 — PDF 파서 & 입력 파이프라인 (재현 가이드)

> **이 문서의 목적**: 누가, 어떤 PC에서 따라 해도 **같은 순서 → 같은 결과**가 나오도록 정리한 표준 레시피.
> 공고문(PDF)을 받아 **agent2가 바로 소비하는 구조화 JSON**으로 바꾸는 것까지가 agent1의 일.

---

## 0. 전체 그림 (3-에이전트 파이프라인)

```
원본 PDF ──▶ [agent1] opendataloader-pdf 파싱 ──▶ agent1_output.json
                                                      (pages/tables/outline/evidence)
            └──────────────▶ [agent2] 분류·추출·요약 ──▶ agent2_output.json + preview.html
                                                              ▲
                                                   [agent3] 대시보드가 소비
```

- **agent1(이 폴더)** = 입력·파싱 계층. PDF → 구조화 JSON.
- **agent2** = 분석 계층. 분류/추출/요약. (`../agent2/`)
- 둘은 **JSON 계약**으로만 연결된다. agent1은 계약(JSON)만 잘 뱉으면 끝.

---

## 1. 사용 도구와 선택 이유

| 도구 | 역할 | 왜 이걸 썼나 |
|---|---|---|
| **[opendataloader-pdf](https://github.com/opendataloader-project/opendataloader-pdf)** | PDF → 의미 단위(heading/표/문단) JSON | Java 11+ 내장, **100% 로컬·오프라인**(민감자료 안전), GPU 불필요, 표·목차까지 구조 추출 |
| Python 3.10+ | 파서 SDK 구동 | opendataloader-pdf의 최소 요구 버전 |

> 핵심 원칙: **추출은 LLM에 맡기지 않고, 파서가 준 구조(title·목차·표) + 정규식으로 결정적으로** 뽑는다.
> LLM(소형 로컬모델)은 정형값에서 빈값/0값을 내기 쉬워, **재현성과 정확도 모두 파서+정규식이 우위**다.
> (LLM은 *자유 서술 요약* 같은 곳에만 선택적으로 사용 — 아래 7절)

---

## 2. 환경 준비 (1회)

```bash
# (1) Python 3.10+ 확인 — 없으면 설치
python3.11 --version            # 이 저장소 기준: /opt/anaconda3/bin/python3.11 (3.11.7)
# 없으면:  brew install python@3.12

# (2) Java 11+ 확인 (opendataloader 엔진)
java -version                   # 없으면:  brew install openjdk

# (3) 파서 설치
python3.11 -m pip install -U opendataloader-pdf      # 또는: -r src/agent1/requirements.txt
```

---

## 3. 실행 (한 줄)

```bash
cd src/agent1

# 방법 A) 스크립트 — python 자동탐지 + (옵션) agent2까지 연결
./run.sh ../../temp_1782793030636.242898756.pdf                  # 파싱만
./run.sh ../../temp_1782793030636.242898756.pdf --with-agent2    # agent1→agent2 전체

# 방법 B) 직접
python3.11 agent1_parse.py <input.pdf>     # 인자 생략 시 루트의 첫 *.pdf 자동 탐색
```

산출: **`src/agent1/agent1_output.json`** (같은 입력 → 항상 같은 출력 = 결정적)

---

## 4. 출력 계약 (agent2가 소비하는 JSON)

```jsonc
{
  "document_id": "DOC-XXXXXXXXXX",       // 파일명 해시(재현 가능)
  "file_name": "....pdf",
  "status": "extracted",                  // agent2가 분석 시작하는 트리거 상태
  "number_of_pages": 37,
  "doc_hint": "R&D 공고(추정)",            // 가벼운 힌트(정식 분류는 agent2)
  "needs_ocr": false,                     // A-07: 평균 글자수로 스캔본 판정
  "pages":    [ { "page_no": 1, "text": "..." }, ... ],            // B-01
  "tables":   [ { "table_id":"T-1","page_no":1,"title":"...",      // B-02
                  "rows":[["셀",...],...], "header":[...], "records":[{...}] } ],
  "outline":  [ { "level": 2, "title": "...", "page_no": 1 }, ... ],// B-04
  "evidence": [ { "evidence_id":"EV-001-01","page_no":1,"text":"..." } ] // B-05
}
```

이 키 구조는 `../agent2/mock_agent1_output.json`(입력 계약 예시)과 호환된다.
agent2는 `AGENT1_OUTPUT=<이 파일 경로>` 환경변수로 이 결과를 그대로 입력받는다.

---

## 5. 변환 알고리즘 (agent1_parse.py 가 하는 일)

opendataloader-pdf 출력은 `kids`로 중첩된 요소 트리다. 이를 평탄화(`walk()`) 후:

| 단계 | 명세 ID | 처리 |
|---|---|---|
| 페이지 텍스트 | B-01 | `heading/paragraph/list/caption` 의 `content`를 `page number`별로 합침 |
| 표 | B-02 | `table` 노드 → 셀 텍스트 그리드 `rows` + 헤더 추정 `records`(헤더 기반 dict행) |
| 목차 | B-04 | `heading` → `{level, title, page_no}` |
| 근거 | B-05 | 핵심 문장에 `EV-{page}-{seq}` id 부여 → 후속 evidence 추적의 전제 |
| OCR 판정 | A-07 | 평균 글자수 < 30 이면 `needs_ocr=true` (스캔본 의심) |

---

## 6. 검증된 실행 결과 (재현 기준값)

입력 `temp_1782793030636.242898756.pdf` (해양수산부 R&D 공고, 37p) 기준:

```
[메타] pages=37  hint=R&D 공고(추정)  needs_ocr=False(130자/페이지)
[B-02 표] 20개 (records 변환 16개)
[B-04 목차] 66개   [B-05 근거] 120개
```

agent2(hybrid) 연결 시 → 사업명·발주처(해양수산부)·선정방식(지정공모)·예산(150억=15,000,000,000원)·
연구개발기간(4년 이내)·평가배점 7항목·과업 27건 추출, **9종 스키마 100% PASS**.

---

## 7. (선택) 요약만 로컬 LLM(Ollama)에 — 정형값은 절대 LLM에 안 맡김

- 추출(예산/기간/배점/과업/제출서류 등)은 **항상 파서+정규식**(결정적).
- *자유 서술 요약*이 더 자연스럽길 원하면 그때만 Ollama 사용:
  ```bash
  brew install ollama && ollama pull qwen2.5:3b
  AGENT2_BACKEND=hybrid AGENT2_HYBRID_LLM=1 python3 ../agent2/agent2_extract.py
  ```
- 8GB RAM M1 기준 qwen2.5:3b(약 2GB) 권장. 대형 모델(예: MiMo-V2-Flash 309B)은 로컬 불가.

---

## 8. 앞으로 새 문서에 적용하는 법 (이 패턴을 그대로 복제)

1. PDF를 루트에 두고 `./run.sh <pdf> --with-agent2` 실행.
2. 결과 JSON 키가 깨지면 4절 계약과 대조 (agent2는 이 계약만 신뢰).
3. 새 문서 유형에서 **정형값 표기가 다르면** → `../agent2/agent2_extract.py`의
   `regex_*`/`parser_*` 함수에 패턴만 추가 (LLM 의존 금지 = 재현성 유지).
4. 표 안에 값이 있으면 agent1이 이미 `tables[].rows/records`로 뽑아주므로 그걸 읽는다.

> **요지**: 파서가 구조를 주고(agent1) → 정규식이 결정적으로 뽑고(agent2) → LLM은 요약 같은 보조에만.
> 이래야 "돌릴 때마다 결과가 같다"는 재현성이 보장된다.
