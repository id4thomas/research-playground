# doc-edit server

FastAPI + LangGraph 기반 문서 편집 백엔드.

## 실행

```bash
# 최초 1회: venv 생성 & 패키지 설치
python3.12 -m venv env
env/bin/pip install -r requirements.txt

# 로컬 개발 서버 (hot reload)
./run-local.sh          # http://localhost:5000
```

## 프로젝트 구조

```
server/
├── src/
│   ├── main.py                        ← FastAPI 앱 & 엔드포인트
│   ├── models.py                      ← Pydantic 모델 전체
│   ├── config.py                      ← 설정 (pydantic-settings)
│   ├── parser/
│   │   └── md_parser.py               ← Markdown → Document 파싱
│   ├── core/
│   │   ├── logger.py
│   │   └── llm/langchain.py           ← ChatOpenAI 팩토리
│   └── agent/
│       └── doc_assistant/
│           ├── graph.py               ← DocAssistantAgent (LangGraph)
│           ├── states.py              ← AgentState TypedDict
│           └── nodes/
│               ├── intent_router.py   ← 인텐트 분류
│               ├── edit.py            ← 블록 수정
│               ├── restructure.py     ← 섹션 구조 변경
│               ├── answer.py          ← 질문 답변
│               └── assembler.py       ← 최종 응답 조합
├── tests/                             ← API 통합 테스트
├── requirements.txt
├── pytest.ini
├── run-local.sh
└── run.sh                             ← 컨테이너 실행용
```

## API 엔드포인트

| 메서드 | 경로 | 설명 |
|---|---|---|
| `POST` | `/api/documents/upload` | Markdown 업로드 → 파싱 |
| `GET` | `/api/documents/{doc_id}` | Document 조회 |
| `POST` | `/api/chat` | 인텐트 자동 분류 후 라우팅 |
| `POST` | `/api/edit` | 블록 본문 수정 (직접 호출) |
| `POST` | `/api/restructure` | 섹션 구조 변경 (직접 호출) |
| `POST` | `/api/answer` | 질문 답변 (직접 호출) |
| `POST` | `/api/clarify` | 명확화 질문 생성 (직접 호출) |

`/api/edit`, `/api/restructure`, `/api/answer`, `/api/clarify`는 인텐트 라우팅을 거치지 않고 해당 에이전트를 직접 호출합니다.
프론트엔드에서 `\edit ...`, `\restructure ...` 같이 백슬래시 prefix를 입력하면 이 엔드포인트가 사용됩니다.

### 요청 형식 (공통)

```json
{
  "project_id": "abc123",
  "messages": [{"role": "user", "content": "문제점 섹션을 보완해줘"}],
  "document": { "sections": {...}, "outline": [...] },
  "selected": ["S1-2;0", "S1-2;1"]
}
```

### 응답 형식

```json
{
  "message": {"role": "assistant", "content": "..."},
  "edits": { "S1-2;0": [{"action": "REWRITE", "value": "새 본문"}] },
  "outline_actions": [],
  "intent": "edit",
  "clarify_options": []
}
```

## 테스트

서버를 먼저 실행한 뒤 별도 터미널에서 pytest를 실행합니다.

```bash
# 터미널 1 — 서버 기동
./run-local.sh

# 터미널 2 — 전체 테스트 실행
env/bin/python -m pytest tests/ -v

# 특정 엔드포인트만 테스트
env/bin/python -m pytest tests/test_edit.py -v
env/bin/python -m pytest tests/test_restructure.py -v
env/bin/python -m pytest tests/test_answer.py -v
env/bin/python -m pytest tests/test_clarify.py -v
env/bin/python -m pytest tests/test_chat.py -v
env/bin/python -m pytest tests/test_upload.py -v
```

### 테스트 파일 구성

| 파일 | 대상 | 주요 검증 항목 |
|---|---|---|
| `test_upload.py` | 문서 업로드·조회 | doc_id 반환, outline 구조, 404 처리 |
| `test_edit.py` | `/api/edit` | edits 생성, ref 형식, 내부 코드 미노출 |
| `test_restructure.py` | `/api/restructure` | outline_actions 생성, 액션 타입, edits 없음 |
| `test_answer.py` | `/api/answer` | 메시지 반환, edits 없음, 한국어 응답 |
| `test_clarify.py` | `/api/clarify` | 질문 반환, options 형식, edits 없음 |
| `test_chat.py` | `/api/chat` | 인텐트 라우팅, selected 처리, 코드 미노출 |

### 서버 주소 변경

기본값은 `http://localhost:5000`입니다. 변경이 필요하면 `tests/conftest.py`의 `BASE_URL`을 수정하세요.

## 환경 변수

`.env.example`을 복사해 `.env`를 만들고 필요한 값을 설정합니다.

```bash
cp .env.example .env
```

| 변수 | 기본값 | 설명 |
|---|---|---|
| `LLM__BASE_URL` | `http://localhost:901/v1` | LLM 서버 주소 |
| `LLM__MODEL` | `Qwen3.6-35B-A3B` | 모델 이름 |
| `LLM__API_KEY` | `EMPTY` | API 키 |
| `TRACING__URI` | `http://localhost:7000` | MLflow 서버 주소 |
| `TRACING__EXPERIMENT` | `2605-doc-editor` | MLflow 실험 이름 |
