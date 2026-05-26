# Agents — LangGraph 기반 멀티에이전트 구조

## 1. 관리 체계 (Agent > Node > Module)

서버는 **3-계층 책임 분리** 구조로 LLM 에이전트를 관리한다.

```
Agent  (LangGraph StateGraph)
  └─ Node  (그래프 1개 step, AgentState 일부를 읽고/쓴다)
        └─ Module  (실제 LLM 호출 + 입출력 Pydantic 모델)
```

| 계층 | 책임 | 위치 |
|---|---|---|
| **Agent** | 그래프 정의 (노드 + 엣지 + 라우팅), 컴파일/실행 진입점 | `agent/doc_*/graph.py` |
| **Node** | state dict 입출력. 1개 module을 호출해 state patch를 반환 | `agent/doc_*/nodes/*.py`, 공용은 `agent/nodes/` |
| **Module** | LLM 호출, 프롬프트 렌더, structured output 파싱 | `agent/modules/*.py` |

### Agent 계층 — `BaseAgent`

```python
# agent/base.py
class BaseAgent(ABC):
    @abstractmethod
    def compile_graph(self) -> CompiledStateGraph: ...

    @abstractmethod
    async def invoke(self, state: dict) -> dict: ...
```

각 구현체는 `compile_graph()`에서 lazy하게 그래프를 빌드/캐시하고, `invoke()`에서 컴파일된 그래프를 `ainvoke`로 실행한다.

### Node 계층 — `BaseNode`

```python
# agent/nodes/base.py
class BaseNode(ABC):
    name: str

    async def __call__(self, state: dict) -> dict:
        try:
            return await self.run(state)
        except Exception as e:
            self._logger.exception("node failed")
            return self.on_error(state, e)

    @abstractmethod
    async def run(self, state: dict) -> dict: ...

    def on_error(self, state, err) -> dict:
        return {}
```

- `__call__`이 로깅과 fallback을 표준화 — 노드가 던지면 빈 patch를 돌려주거나 module별 default 출력을 채워준다.
- Node는 **상태 dict → 부분 patch dict**를 반환하는 순수 함수처럼 동작한다. LangGraph가 patch를 state에 머지한다.

### Module 계층

각 module은 (a) Pydantic 입출력 모델, (b) prompt YAML 로딩, (c) LLM 호출 + structured output 파싱을 캡슐화한다.

```
agent/modules/
├── intent_classify.py       — Intent Router
├── context_collect.py        — 본문 로드 대상 섹션 선정
├── edit_generate.py          — 블록 수정안 생성
├── restructure_generate.py   — 섹션 트리 변경안 생성
├── answer_generate.py        — 자연어 답변
├── clarify_generate.py       — 질문 + 선택지
├── edit_assemble.py          — LLMEdit → API Edit 변환
└── strip_codes.py            — 메시지에서 내부 코드(S1 등) 제거
```

---

## 2. 지원 에이전트 종류

| 에이전트 | 역할 | 구성 |
|---|---|---|
| `DocAssistantAgent` | **통합 라우터**. intent 분류 후 4개 서브그래프 중 하나로 분기 | `intent_router → {editor / restructurer / answerer / clarifier}` |
| `DocEditorAgent` | 블록 본문 수정 | `context_collector → edit → assemble` |
| `DocRestructurerAgent` | 섹션 이름·계층 변경 | `restructure → assemble` |
| `DocAnswererAgent` | 문서 기반 질의응답 | `context_collector → answer → assemble` |
| `DocClarifierAgent` | 추가 질문 + 선택지 생성 | `clarify → assemble` |

서브에이전트는 **단독 호출도 가능**하다 — `POST /api/chat/{edit|restructure|answer|clarify}`로 intent router를 건너뛰고 곧장 진입한다.

### 통합 흐름 (`DocAssistantAgent`)

```
              START
                │
                ▼
        intent_router
                │
       ┌────────┼────────────┬──────────────┐
       ▼        ▼            ▼              ▼
   editor   restructurer   answerer    clarifier
       │        │            │              │
       └────────┴────────────┴──────────────┘
                              │
                             END
```

라우팅 함수는 `intent_router.intent` 값(`edit` / `restructure` / `answer` / `clarify`) 기준으로 분기한다. 누락/오류 시 `clarify`로 폴백.

---

## 3. AgentState — 그래프 공유 상태

### `AgentState` (doc_assistant, 최상위)

```python
# agent/doc_assistant/states.py
class AgentState(TypedDict, total=False):
    # 입력
    messages: Annotated[list[BaseMessage], add_messages]
    document: Document
    selected: list[str] | None

    # 노드별 출력 (module output 그대로 저장)
    intent_router: IntentRouterOutput
    context: ContextCollectOutput
    edit: EditOutput
    restructure: RestructureOutput
    answer: AnswerOutput
    clarify: ClarifyOutput

    # 최종 응답 객체 (assembler가 채움)
    final: FinalOutput
```

`total=False` — 모든 키가 선택적이라 노드는 자신이 쓰는 키만 채우면 된다.

### `FinalOutput` — 어떤 서브그래프든 동일 형식

```python
class FinalOutput(BaseModel):
    message: str = ""
    edits: dict[str, list[Edit]] = Field(default_factory=dict)
    outline_actions: list[OutlineAction] = Field(default_factory=list)
    clarify_options: list[str] = Field(default_factory=list)
```

→ assembler 노드는 자신의 intent에 해당하는 필드만 채우고 나머지는 기본값. `api/chat/service.py`가 `state["final"]`을 꺼내 `ChatResponse`로 매핑한다.

### 서브그래프별 state

각 서브에이전트는 자체 `TypedDict` state를 가진다. 모두 `messages` / `document` / `selected` / `final`을 공유하고, 자기 분기에 필요한 module output만 추가로 갖는다.

```python
class EditorState(TypedDict, total=False):
    messages: ...; document: ...; selected: ...
    intent_router: IntentClassifyOutput     # 부모에서 전달 (target_sections 힌트용)
    context: ContextCollectOutput
    edit: EditGenerateOutput
    final: FinalOutput

class RestructurerState(TypedDict, total=False):
    # outline만 보면 충분 — context_collector 없음
    messages: ...; document: ...; selected: ...
    restructure: RestructureGenerateOutput
    final: FinalOutput

class AnswererState(TypedDict, total=False):
    messages: ...; document: ...; selected: ...
    intent_router: IntentClassifyOutput
    context: ContextCollectOutput
    answer: AnswerGenerateOutput
    final: FinalOutput

class ClarifierState(TypedDict, total=False):
    messages: ...; document: ...; selected: ...
    clarify: ClarifyGenerateOutput
    final: FinalOutput
```

---

## 4. 노드별 state 업데이트

각 노드는 `run(state) → patch dict`를 반환한다. 아래는 노드가 **읽는 키**와 **쓰는 키**, 그리고 patch의 모양.

### `intent_router`

```
read:   messages, document, selected
write:  {"intent_router": IntentClassifyOutput}
```

```python
async def run(self, state):
    out = await classify_intent(
        messages=state["messages"],
        document=state["document"],
        selected=state.get("selected"),
    )
    return {"intent_router": out}
```

출력: `intent`, `target_sections`, `suggest_new_session`, `suggest_new_session_reason`, `token_usage`.

### `context_collector`

```
read:   messages, document, selected, intent_router (force/hint sections)
write:  {"context": ContextCollectOutput}
```

intent_router의 `target_sections`를 힌트로 받아, "실제 블록 본문을 봐야 할 섹션 코드 목록"을 LLM이 좁혀준다. `selected`된 블록의 섹션은 자동 포함, outline에 없는 코드는 폐기.

### `edit` / `restructure` / `answer` / `clarify`

각자의 module을 호출해 결과를 본인 키에 저장.

```python
# edit 노드
return {"edit": EditGenerateOutput(edits=[...], message=..., token_usage=...)}

# restructure 노드
return {"restructure": RestructureGenerateOutput(actions=[...], message=..., ...)}

# answer 노드
return {"answer": AnswerGenerateOutput(message=..., token_usage=...)}

# clarify 노드
return {"clarify": ClarifyGenerateOutput(question=..., options=[...], ...)}
```

`edit_node`는 `intent_router.target_sections` → `context.section_codes` 순으로 우선순위를 풀어 `target_sections`를 결정한다.

### Assembler 노드 — 최종 결과 정리

각 서브그래프 끝에는 자신의 module output을 `FinalOutput`으로 변환하는 assembler가 있다.

| Assembler | 입력 키 | `FinalOutput` 채움 |
|---|---|---|
| `edit_assemble` | `state["edit"]` | `message` + `edits` (`LLMEdit → Edit` 변환 + ref별 그룹화) |
| `restructure_assemble` | `state["restructure"]` | `message` + `outline_actions` |
| `answer_assemble` | `state["answer"]` | `message`만 |
| `clarify_assemble` | `state["clarify"]` | `message` (= question) + `clarify_options` |

공통 처리:
1. `strip_section_codes(message, document)` — LLM이 흘린 내부 코드(`S1`, `S1-2;0` 등)를 한국어 섹션 제목으로 치환.
2. `edit_assemble`은 추가로 **ref 단위 그룹화** + 액션 규칙 강제 (`enforce_action_rules_map`):
   - 같은 ref에 REWRITE가 있으면 그 ref의 REPLACE/INSERT 제거.
   - REWRITE 여러 개는 첫 번째만 유지.

```python
# agent/modules/edit_assemble.py
def edits_to_map(llm_edits: list[LLMEdit]) -> dict[str, list[Edit]]:
    out = {}
    for le in llm_edits:
        api = llm_edit_to_api(le)   # REWRITE → RewriteEdit, REPLACE → ReplaceEdit, ...
        if api:
            out.setdefault(le.ref, []).append(api)
    return enforce_action_rules_map(out)
```

### `api/chat/service.py` — FinalOutput → ChatResponse

서브그래프 실행 후 `state["final"]`을 꺼내 API 응답으로 변환한다. token 사용량은 state 내 모든 `*_output.token_usage`를 합산.

```python
def aggregate_usage(state: dict) -> TokenUsage:
    total = TokenUsage()
    for key in ("intent_router", "context", "edit", "restructure", "answer", "clarify"):
        out = state.get(key)
        if out and out.token_usage:
            total = total.add(out.token_usage)
    return total
```

---

## 5. `core.langchain` — LLM 호출 / 구조화 출력

### 5-1. 모델 선언 (`core/langchain/llm.py`)

`ChatOpenAI` 기반의 OpenAI-호환 클라이언트를 thin wrapper로 감쌌다. 설정은 `config.py`의 `LLMClientConfig`에서 읽는다.

```python
class LangChainChatModel:
    @classmethod
    def get_model(cls, *, model_name=None, temperature=None, max_completion_tokens=None, **kwargs):
        params = {
            "model":    model_name or settings.llm.model,
            "base_url": settings.llm.base_url,      # ex: http://localhost:901/v1
            "api_key":  settings.llm.api_key,       # "EMPTY"
        }
        if temperature is not None: params["temperature"] = temperature
        if max_completion_tokens is not None: params["max_completion_tokens"] = max_completion_tokens
        params.update(kwargs)
        return ChatOpenAI(**params)
```

### 5-2. 프롬프트 + 모델 설정 번들 (`core/prompts.py`)

각 module은 `agent_spec`을 YAML에서 로드해서 system 프롬프트와 모델 파라미터, output schema를 한 곳에서 관리한다.

```yaml
# prompts/intent_classify.yaml
name: intent_classify
model:
  temperature: 0
  extra_body:
    chat_template_kwargs:
      enable_thinking: false
output_schema: agent.modules.intent_classify:_LLMOut
input_variables: [outline_text, selected_text]
prompt:
  system: |
    당신은 ... Intent Router입니다.
    ## 문서 Outline
    {{ outline_text }}
    ## 선택된 블록
    {{ selected_text }}
```

`load_agent_spec("intent_classify")`가 lru_cache로 1회 파싱해 `AgentSpec`을 돌려준다.

```python
@dataclass
class AgentSpec:
    name: str
    _system_template: str
    input_variables: list[str]
    model_kwargs: dict[str, Any]         # → LangChainChatModel.get_model(**model_kwargs)
    output_schema: type | None           # dotted-path "pkg.mod:Attr"에서 해석

    def render_system(self, **vars) -> str:
        # Jinja2 StrictUndefined — 필수 변수 누락 시 예외
        # 자동으로 HISTORY_FORMAT_NOTE를 앞에 부착 (LLM이 [ASSISTANT · ...] 태그 해석)
        ...
```

### 5-3. Structured Output 패턴

전 module이 동일 패턴을 따른다 — `with_structured_output(schema, include_raw=True)`로 LLM이 Pydantic 객체를 곧장 뱉게 하고, raw 응답에서 token usage를 함께 회수한다.

```python
async def classify_intent(messages, document, selected):
    spec = load_agent_spec("intent_classify")
    system_prompt = spec.render_system(outline_text=..., selected_text=...)

    llm = LangChainChatModel.get_model(**spec.model_kwargs).with_structured_output(
        spec.output_schema,
        include_raw=True,
    )
    try:
        raw = await llm.ainvoke([SystemMessage(content=system_prompt)] + list(messages))
        result: _LLMOut = raw["parsed"]
        usage = TokenUsage.from_message(raw)
    except Exception as e:
        logger.warning("structured output failed — fallback")
        return IntentClassifyOutput(intent="clarify")    # 모듈별 fallback
    return IntentClassifyOutput(**result.model_dump(), token_usage=usage)
```

`include_raw=True` 응답 형태:
```python
{"raw": AIMessage(...), "parsed": <_LLMOut>, "parsing_error": None}
```

### 5-4. Token Usage (`core/langchain/usage.py`)

```python
class TokenUsage(BaseModel):
    input: int = 0
    output: int = 0       # reasoning 제외 순수 출력
    reasoning: int = 0    # 모델이 내부적으로 쓴 thinking 토큰

    @classmethod
    def from_message(cls, msg) -> "TokenUsage":
        # include_raw dict, LangChain AIMessage, OpenAI response_metadata 모두 처리
        ...
    def add(self, other) -> "TokenUsage": ...
```

assembler 시점에 각 module이 자기 `token_usage`를 자신의 output에 박아두고, `service.aggregate_usage()`가 그래프 종료 후 모두 합산한다.

---

## 6. mlflow Tracing

LangGraph는 mlflow `langchain.autolog()`로 자동 추적한다. `config.py`의 `TracingConfig.enabled`로 on/off.

### 부팅 시점 (`main.py` lifespan)

```python
if settings.tracing.enabled:
    mlflow.set_tracking_uri(settings.tracing.uri)         # ex: http://localhost:7000
    mlflow.set_experiment(settings.tracing.experiment)    # ex: "2605-doc-editor"
    mlflow.langchain.autolog()                            # LangChain/LangGraph 자동 캡처
```

### 수동 span (`core/tracing.py`)

서비스 코드는 직접 mlflow에 의존하지 않고 thin wrapper만 쓴다. disabled일 때는 no-op이 반환된다.

```python
from core.tracing import start_span

with start_span("chat_request") as span:
    span.set_inputs({"project_id": req.project_id, "selected": req.selected})
    result = await _assistant.invoke(initial_state(req))
    span.set_outputs({"intent": resp_intent, "final_message": final.message})
```

→ mlflow UI에서 `chat_request` 트레이스 안에 LangGraph 노드 / LLM 호출 / structured output 파싱이 모두 nested span으로 자동 기록된다.

### 설정 (`.env`)

```
TRACING__ENABLED=true
TRACING__URI=http://localhost:7000
TRACING__EXPERIMENT=2605-doc-editor
```

`env_nested_delimiter="__"`로 pydantic-settings가 중첩 모델에 매핑.

---

## 7. 폴더 구조 요약

```
server/src/agent/
├── base.py                       BaseAgent
├── doc_assistant/                통합 라우터
│   ├── graph.py                  intent → 4-way 분기
│   ├── states.py                 AgentState, FinalOutput
│   └── nodes/intent_router.py
├── doc_editor/                   blocks 수정 서브그래프
│   ├── graph.py
│   └── nodes/{edit,assemble}.py
├── doc_restructurer/             outline 수정 서브그래프
├── doc_answerer/                 QA 서브그래프
├── doc_clarifier/                clarify 서브그래프
├── nodes/                        공용 노드 (context_collector 등)
│   ├── base.py                   BaseNode
│   └── context_collector.py
└── modules/                      LLM 호출 + Pydantic 모델 (그래프-독립)
    ├── intent_classify.py
    ├── context_collect.py
    ├── edit_generate.py
    ├── restructure_generate.py
    ├── answer_generate.py
    ├── clarify_generate.py
    ├── edit_assemble.py          LLMEdit → API Edit 변환
    └── strip_codes.py
```
