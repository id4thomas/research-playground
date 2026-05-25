# Backend — FastAPI 서버

채팅 기반 문서 편집을 위한 FastAPI 백엔드. LangGraph 멀티에이전트를 thin HTTP 레이어로 감싸 노출한다.

## 1. 큰 그림

```
┌─────────────────────────────────────────────────────────────┐
│  api/        — HTTP 표면 (FastAPI router + DTO + service)   │
│   │                                                          │
│   ├─ parse/   POST /api/parse                               │
│   └─ chat/    POST /api/chat[/edit|restructure|answer|...]  │
│        │                                                     │
│        ▼                                                     │
│  agent/      — LangGraph 에이전트 (intent 라우팅 + 서브그래프)  │
│        │                                                     │
│        ▼                                                     │
│  core/       — 도메인 공통 (LLM wrapper, 데이터 모델, tracing) │
│   ├─ data/        Document / Edit / OutlineAction           │
│   ├─ dto/         ApiRequest / ApiResponse 봉투             │
│   ├─ langchain/   LLM 클라이언트, token usage                │
│   ├─ prompts.py   YAML AgentSpec 로더                       │
│   └─ tracing.py   mlflow span wrapper                       │
└─────────────────────────────────────────────────────────────┘
```

설계 원칙:

- **Stateless 서버**: 문서/채팅 히스토리는 프론트엔드가 보관, 매 요청에 전체를 다시 보낸다. 서버에는 세션·DB 없음.
- **3-계층 분리** (api → agent → core): 위 계층은 아래만 안다. core는 어디서도 import 가능한 순수 도메인.
- **표준 응답 봉투**: 모든 엔드포인트가 `ApiResponse[T]`로 감싸 일관된 `{code, message, data}` 포맷 반환.
- **얇은 service**: 라우터는 service 함수 1개만 호출, service는 agent를 호출하고 응답 매핑만 담당. 비즈니스 로직은 agent에 있다.

---

## 2. `api/` — HTTP 표면

### 모듈 단위 = 엔드포인트 한 묶음

각 엔드포인트 그룹은 4개 파일로 동일한 구조를 따른다:

```
api/<endpoint>/
├── router.py     FastAPI APIRouter 정의 (경로 → service)
├── service.py    비즈니스 로직 (대부분 agent 호출 + 응답 매핑)
├── dto.py        Pydantic 요청/응답 모델
└── __init__.py
```

router는 얇게 유지한다 — 검증·실행·매핑은 service에서.

```python
# api/chat/router.py
@router.post("", response_model=ApiResponse[ChatResponse])
async def chat_endpoint(request: ApiRequest[ChatRequest]) -> ApiResponse[ChatResponse]:
    data = await run_chat(request.data)        # ← service 한 줄
    return ApiResponse(code=0, message="success", data=data)
```

### 두 그룹: `parse` / `chat`

| 그룹 | 책임 | 특징 |
|---|---|---|
| `api/parse` | Markdown 업로드 → `Document` 트리로 파싱 | LLM 미사용, 순수 텍스트 처리 |
| `api/chat` | 대화 처리 → LangGraph 실행 → 수정안/답변 반환 | 5개 엔드포인트 (`/`, `/edit`, `/restructure`, `/answer`, `/clarify`) |

`chat`은 통합 엔드포인트(`/api/chat`, intent 분기 포함)와 서브그래프 직접 호출(`/api/chat/{intent}`)을 함께 노출한다. 프론트엔드가 액션을 사용자에게 명시적으로 선택하게 하면 intent router 비용을 아낄 수 있다.

### 표준 응답 봉투

```python
# core/dto
class ApiRequest[T](BaseModel):
    data: T

class ApiResponse[T](BaseModel):
    code: int = 0
    message: str = "success"
    data: Optional[T] = None
```

성공은 `code=0`, 실패는 exception handler가 잡아서 코드를 분류한다 (`1000` unknown / `2000` LLM API / `2010` LLM timeout / `3000` graph execution). 모든 실패 응답에 traceback이 `data`로 들어가 디버깅이 쉽다.

---

## 3. `agent/` — LangGraph 에이전트

`agent/` 아래는 **에이전트 단위**로 디렉토리가 나뉜다. 각 에이전트는 자기 그래프 정의·노드·state를 소유하고, 공용 노드(`agent/nodes/`)와 LLM 호출 모듈(`agent/modules/`)을 가져다 쓴다.

```
agent/
├── base.py                 BaseAgent (compile_graph, invoke)
├── doc_assistant/          통합 라우터 (intent → 서브그래프 분기)
├── doc_editor/             블록 본문 수정
├── doc_restructurer/       섹션 트리 변경
├── doc_answerer/           문서 기반 QA
├── doc_clarifier/          질문 + 선택지 생성
├── nodes/                  공용 노드 (context_collector 등)
└── modules/                LLM 호출 + 입출력 Pydantic 모델
```

3계층 책임 분리 (Agent > Node > Module), 각 그래프의 state 구조, assembler 정리 방식 등 자세한 내용은 [`agents.md`](agents.md) 참조.

api 레이어 시점에서 알 것:
- service 함수는 `agent.invoke(initial_state)` 한 번 호출하고 `state["final"]` (= `FinalOutput`)을 `ChatResponse`로 매핑한다.
- `FinalOutput`은 모든 서브그래프가 동일하게 채우는 정규화된 결과 객체 (`message` / `edits` / `outline_actions` / `clarify_options`).

### ChatResponse — intent별 반환 예시

`ChatResponse`의 필드 형태는 동일하지만, intent에 따라 채워지는 필드가 다르다.

```python
class ChatResponse(BaseModel):
    message: ChatMessage                          # 항상 채워짐
    edits: dict[str, list[Edit]] = {}             # edit에서만
    outline_actions: list[OutlineAction] = []     # restructure에서만
    clarify_options: list[str] = []               # clarify에서만
    intent: str = ""
    suggest_new_session: bool = False
    suggest_new_session_reason: str | None = None
    token_usage: TokenUsage
```

#### (1) `intent="edit"` — 블록 수정 제안

```json
{
  "message": {
    "role": "assistant",
    "content": "'문제점' 섹션의 첫 번째 블록을 보완하고, 두 번째 블록 안의 표현 하나를 다듬었습니다."
  },
  "intent": "edit",
  "edits": {
    "S1-2;0": [
      { "action": "REWRITE",
        "value": "기존 접근 방식은 고정된 섹션 구조를 가정하여 범용 문서 적용이 어렵다...",
        "summary": "한계점을 더 구체적으로 보완" }
    ],
    "S1-2;1": [
      { "action": "REPLACE", "source": "한계가 있다", "target": "구조적 한계가 존재한다",
        "summary": "표현을 명확하게 다듬음" }
    ]
  },
  "outline_actions": [],
  "clarify_options": []
}
```

같은 블록에 INSERT가 함께 올 수도 있다:

```json
"S2;0": [
  { "action": "REPLACE", "source": "...", "target": "...", "summary": "오타 수정" },
  { "action": "INSERT",
    "value": { "type": "text", "content": "이를 통해 적용 범위가 확장된다." },
    "summary": "결론 문장 추가" }
]
```

> 단, 같은 ref에 `REWRITE`가 있으면 다른 액션은 assembler가 제거한다.

#### (2) `intent="restructure"` — 섹션 트리 변경

```json
{
  "message": {
    "role": "assistant",
    "content": "'배경기술' 섹션을 '관련 연구'로 이름을 바꾸고, 그 아래 '한계 분석' 섹션을 새로 추가했습니다."
  },
  "intent": "restructure",
  "edits": {},
  "outline_actions": [
    { "action": "RENAME", "target": "S1", "title": "관련 연구" },
    { "action": "ADD", "target": "S1", "title": "한계 분석", "position": 2 }
  ],
  "clarify_options": []
}
```

MERGE 예시:

```json
{ "action": "MERGE", "targets": ["S1-1", "S1-2"], "title": "선행 기술 및 한계" }
```

#### (3) `intent="answer"` — 메시지만

수정 없음. message만 채워진다.

```json
{
  "message": {
    "role": "assistant",
    "content": "이 문서는 배경기술, 해결 수단, 효과 세 부분으로 구성되어 있습니다. 배경기술에서는 종래 기술의 한계를..."
  },
  "intent": "answer",
  "edits": {},
  "outline_actions": [],
  "clarify_options": []
}
```

#### (4) `intent="clarify"` — 질문 + 선택지

`message.content`가 어시스턴트 질문, `clarify_options`가 클릭 가능한 보기.

```json
{
  "message": {
    "role": "assistant",
    "content": "'문제점' 섹션을 어떤 방향으로 보완할까요?"
  },
  "intent": "clarify",
  "edits": {},
  "outline_actions": [],
  "clarify_options": [
    "현재 내용을 더 구체적으로 풀어쓰기",
    "기술 용어를 일반 독자 수준으로 쉽게 바꾸기",
    "관련 사례를 추가"
  ]
}
```

→ 사용자가 보기를 클릭하면 프론트엔드가 다음 요청에 `picked_option_index`로 어느 보기를 골랐는지 표시한다.

#### (5) `suggest_new_session=true` — 세션 분리 권장

intent와 무관하게 router가 "이건 별도 세션이 적합" 판단할 수 있다. 프론트엔드는 배지/토스트로 안내만 하고 동작은 기존대로 진행.

```json
{
  "message": { "role": "assistant", "content": "..." },
  "intent": "edit",
  "edits": { ... },
  "suggest_new_session": true,
  "suggest_new_session_reason": "지금까지의 대화가 '배경기술' 섹션 중심이었는데, 새 요청은 '해결 수단' 섹션 전반의 재작성에 가깝습니다."
}
```

---

## 4. `core.data` — 도메인 모델이 서비스와 오가는 방식

`core.data`는 외부 의존성 없는 순수 Pydantic 도메인 모델. **api · agent · 프론트엔드가 모두 같은 모델을 공유**한다는 것이 핵심이다 — `Document`, `Edit`, `OutlineAction`은 와이어 포맷이면서 동시에 내부 데이터 구조다.

### `Document` — 양방향으로 전체가 흐른다

```
프론트엔드                            서버
   │                                  │
   │ ── POST /api/parse (file) ─────► │
   │                                  │   md_parser → Document
   │ ◄──────── ApiResponse[Document] ─│
   │                                  │
   │ Document를 React state로 보관     │
   │                                  │
   │ ── POST /api/chat (Document) ──► │
   │     (매 요청에 전체 트리 동봉)    │   agent가 읽고 LLM에 포매팅 주입
   │ ◄────── ChatResponse (edits) ────│
   │ applyEdit(document, edits)       │
   │ → state 업데이트                  │
```

서버는 Document를 저장하지 않는다. 프론트엔드가 단일 진실의 원천(SSOT)이고, 서버는 매 요청마다 stateless하게 받아 처리한다.

```python
class Document(BaseModel):
    sections: dict[str, Section]    # 검색용: 섹션코드 → Section
    outline:  list[SectionMeta]     # 표시용: 순서/계층 보존
```

두 자료구조는 같은 정보를 다른 인덱스로 들고 있어 동기화된 채 함께 직렬화된다.

### `Edit` — 서버가 만들고 프론트엔드가 적용한다

`Edit`은 "이 블록에 이렇게 바꾸자"는 **제안**이지 변경된 본문이 아니다. 서버는 제안만 보내고, 사용자가 수락해야 프론트엔드가 Document에 반영한다.

```python
# 응답에서: ref(블록 식별자) → 액션 리스트
edits: dict[str, list[Edit]] = {
    "S1-2;0": [RewriteEdit(value="...", summary="...")],
    "S1-2;1": [ReplaceEdit(source="A", target="B", summary="...")],
}
```

서버 내부에서는 LLM → API 사이 **2단계 모델 변환**이 일어난다:

```
LLM 출력 (평탄)             서버 변환 (좁힘)           API 응답 (그룹화)
─────────────────           ─────────────              ───────────────
LLMEdit(                    RewriteEdit | ...         dict[ref, list[Edit]]
  ref, action,        →       ↑                  →
  value?, source?,            llm_edit_to_api()       edits_to_map()
  target?, ...)               + 규칙 검증              + 액션 규칙 강제
```

- `LLMEdit`: LLM이 직접 뱉는 평탄한 모델 (액션마다 다른 필드들이 모두 optional).
- `Edit = RewriteEdit | ReplaceEdit | InsertEdit`: discriminated union으로 좁혀진 안전한 API 모델.
- assembler가 `LLMEdit → Edit`로 변환 + ref별로 그룹화 + 규칙 강제 (같은 ref에 REWRITE 있으면 다른 액션 제거 등).

→ 프론트엔드는 항상 좁혀진 `Edit`만 본다. 평탄 모델은 서버 내부 구현 디테일.

| 액션 | 효과 | 필수 필드 |
|---|---|---|
| `REWRITE` | 블록 본문 전체 교체 | `value` |
| `REPLACE` | 블록 내 substring 치환 | `source`, `target` |
| `INSERT` | 해당 블록 바로 아래 새 블록 추가 | `value` (Block 통째) |

### `OutlineAction` — 섹션 트리 변경

본문은 그대로 두고 섹션 메타(제목/계층/순서)만 바꾼다. restructure 에이전트 전용 출력.

```python
class OutlineAction(BaseModel):
    action: Literal["RENAME", "ADD", "REMOVE", "MERGE"]
    target / targets / title / level / position  # 액션별로 다른 필드 사용
```

`Edit`과 마찬가지로 서버는 제안만 보내고, 프론트엔드가 수락 시 outline에 적용한다.

### import 그래프

```
api/parse      ─→ core.data (Document, Block, ...)
api/chat       ─→ core.data (Document, Edit, OutlineAction)
agent/modules  ─→ core.data (LLMEdit + 위 전부)
agent/doc_*    ─→ agent/modules + core.data
```

`core.data`가 의존성 그래프의 leaf — 어디서 import해도 순환이 생기지 않는다. 프론트엔드 TypeScript 타입(`types/index.ts`)도 이 모델과 1:1 매핑된다.

---

## 5. 설정 & 운영

`config.py`가 `pydantic-settings`로 `.env`를 읽어 4개 영역으로 묶는다:

| 영역 | 내용 |
|---|---|
| `LLM__*` | OpenAI-호환 base_url / api_key / model |
| `TRACING__*` | mlflow tracking uri / experiment / on-off |
| `LOGGING__*` | log_level / format (console·json) |
| `AGENT__*` | 에이전트 동작 옵션 (현재 비어 있음) |

부팅 시 `main.py` lifespan에서 `mlflow.langchain.autolog()`를 활성화하면, LangGraph 노드·LLM 호출·structured output 파싱이 자동으로 trace에 잡힌다. service 코드는 `core.tracing.start_span` wrapper만 쓰면 되고, tracing disabled일 땐 no-op이 반환된다.

자세한 LLM 클라이언트 / structured output / token usage 패턴은 [`agents.md`](agents.md) §5 참조.
