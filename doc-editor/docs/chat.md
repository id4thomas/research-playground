# Chat — 히스토리 누적 & 메시지 스펙

채팅 기반 문서 편집에서 **대화 히스토리가 어떻게 쌓이는지**를 문서 수정 시나리오 중심으로 정리한다.
메시지 표현은 두 갈래로 분리돼 있다 — 프론트엔드와 주고받는 **wire 스펙**과, LLM에 넣는 **LLM 스펙**.

---

## 1. 두 개의 메시지 스펙

| | wire 스펙 | LLM 스펙 |
|---|---|---|
| 정의 위치 | `core/data/chat.py` (`ChatMessage`) | `agent/base.py` (`LLMChatMessage`) |
| 주고받는 주체 | 프론트엔드 ↔ 서버 | 서버 내부 → LLM |
| 블록 참조 | 블록 **UUID** (`ref`) | 블록 **UUID**를 `[uuid]`로 노출 + 대상 설명·요약·상태 텍스트 |
| 구조 | `actions[]` 구조화 | `{role, content}` 텍스트 |
| 변환 | — | `api/chat/serialize.py::wire_to_llm()` |

**핵심 원칙**

- 서버는 **stateless**. 문서와 채팅 히스토리는 프론트엔드가 보관하고, 매 요청에 전체를 다시 보낸다.
- 어시스턴트가 제안한 변경은 응답 메시지의 `actions[]`(블록 UUID 참조)로 전달된다. 프론트엔드는 이를 그대로 반영/리플레이한다.
- 블록은 안정적인 **UUID**로 식별된다. 편집/삽입/삭제가 누적돼도 id는 불변이라 히스토리 ref가 어긋나지 않는다.

---

## 2. wire 메시지 모양

메시지는 `type` 디스크리미네이터로 구분되며, 각 타입은 자기 페이로드만 갖는다:

| type | 주체 | 추가 필드 |
|---|---|---|
| `base` | user/assistant/system | (없음) |
| `interaction` | assistant | `actions[]` (문서 변경) |
| `clarify` | assistant | `clarify_options[]` (선택지 제시) |
| `option_reply` | user | `picked_option_index` (선택지 선택) |

```jsonc
// 단순 텍스트 턴
{ "type": "base", "role": "user", "content": "도입부를 더 간결하게 해줘" }

// 문서 수정이 동반된 턴
{
  "type": "interaction",
  "role": "assistant",
  "content": "'도입부' 섹션의 첫 문단을 간결하게 다듬었습니다.",
  "actions": [
    {
      "scope": "block", "action": "REWRITE",
      "ref": "867b7992adec474ab99b864139da3761",   // 대상 블록 UUID
      "summary": "장황한 배경 설명을 한 문장으로 압축",
      "target_desc": "'도입부' 섹션 내 블록",
      "status": "pending",                          // 아직 사용자가 결정 안 함
      "block": { "type": "text", "id": "867b...", "content": "본 연구는 ... 다룬다." }
    }
  ]
}
```

`status` 의 의미 (히스토리 누적의 핵심):

| status | 의미 |
|---|---|
| `pending` | 제안만 됨, 사용자가 아직 수락/거절 안 함 |
| `accepted` | 사용자가 수락 → **현재 문서가 이미 그 변경 이후 상태** |
| `declined` | 거절됨 → 문서에 반영 안 됨 |
| `instructed` | "이렇게 말고 저렇게" 식 직접 지시 → 다음 턴에서 재편집됨 (`instruction` 필드) |

---

## 3. 히스토리가 쌓이는 흐름

매 턴마다 프론트엔드는 다음을 한다:

1. 직전 어시스턴트 턴의 각 action에 **사용자 결정**(`status`)을 기록한다.
2. 수락된 action은 자신이 들고 있는 Document에 적용한다 (블록 UUID로 찾아 교체/삽입/삭제).
3. 새 user 메시지를 덧붙이고, **(갱신된 문서 + 전체 히스토리)** 를 다시 서버로 보낸다.

서버는 받은 wire 히스토리를 `wire_to_llm()` 으로 직렬화해 LLM에 넘긴다. 이때 블록 **UUID를 `[uuid]`로
함께 노출**하고, 대상 설명·요약·결정 상태도 텍스트로 풀어쓴다.

```
[USER] 도입부를 더 간결하게 해줘
[ASSISTANT · 편집 제안] '도입부' 섹션의 첫 문단을 간결하게 다듬었습니다.

[제시된 문서 액션]
  #1 [REWRITE] [b1] '도입부' 섹션 내 블록 → 수락
      · 의도: 장황한 배경 설명을 한 문장으로 압축
      · 내용: 본 연구는 ... 다룬다.
```

→ LLM은 "`b1` 블록은 이미 압축됐고(수락), 현재 문서의 `[b1]`이 그 상태"라고 해석한다. 대상은 `[b1]` UUID로 가리키며, '도입부 섹션 내 블록'은 섹션 맥락만 주는 보조 표기다. (예전의 '1번째 블록' 같은 상대 위치 표현은 쓰지 않는다 — 편집이 누적되면 순서가 어긋나기 때문.)

### 왜 UUID를 노출하나

함께 보내는 `document`도 편집 LLM에게 `render_document`로 직렬화되는데, 거기서 각 블록은
`[<uuid>] (type) content` 형태로 출력된다. **히스토리 액션의 `[b1]`과 문서 렌더의 `[b1]`이 같은 키**
이므로, 모델은 "이 히스토리 액션이 지금 문서의 어느 블록인지"를 **상대 위치 추론 없이 결정적으로**
찾을 수 있다.

`target_desc`는 섹션 맥락("'도입부' 섹션 내 블록")만 담고, **'N번째 블록' 같은 상대 위치는 쓰지
않는다** — 그 사이 다른 편집으로 순서가 바뀌면 오히려 오해를 부르기 때문이다. 블록 식별은 전적으로
`[uuid]`가 맡고, `target_desc`는 사람이 읽기 위한 섹션 힌트로만 곁들인다.

> 직렬화 형식: `[ref]`가 있으면 `[<uuid>] <target_desc>`, 없으면 `target_desc`만, 둘 다 없으면 `ref`.
> 삽입(INSERT)처럼 아직 문서에 없는 새 블록 id(`bNEW`)는 매칭이 안 되지만, 새 블록이라 원본 참조가
> 불필요하다. 삭제·병합으로 사라진 UUID도 현재 문서 렌더에 없으므로 모델이 "더는 존재하지 않음"을 알 수 있다.

---

## 4. 시나리오 모음

아래 예시는 모두 **wire 히스토리(프론트 보관)** 가 턴이 지날수록 어떻게 누적되는지를 보여준다.
편의상 UUID는 `b1`, `b2` … 로 줄여 표기한다.

### 시나리오 A — 제안 → 수락

> 사용자가 편집을 요청하고, 제안을 받아들인다.

**Turn 1** — 요청

```jsonc
// 프론트 → 서버 (messages)
[ { "type":"base", "role":"user", "content":"배경 섹션 첫 문단을 줄여줘" } ]
```

```jsonc
// 서버 → 프론트 (message)
{
  "type":"interaction", "role":"assistant", "content":"'배경' 섹션 첫 문단을 줄였습니다.",
  "actions":[
    {
      "scope":"block",
      "action":"REWRITE",
      "ref":"b1",
      "summary":"3문장을 1문장으로 축약",
      "target_desc":"'배경' 섹션 내 블록",
      "status":"pending"
      ,"block":{"type":"text","id":"b1","content":"요약된 문단"}
    }
  ]
}
```

**프론트 처리**: 사용자가 "적용" 클릭 → `b1` 블록을 새 content로 교체, action.status를 `accepted`로 기록.

**Turn 2** — 다음 요청 시 보내는 히스토리

```jsonc
[
  { "type":"base", "role":"user", "content":"배경 섹션 첫 문단을 줄여줘" },
  { "type":"interaction", "role":"assistant", "content":"'배경' 섹션 첫 문단을 줄였습니다.",
    "actions":[
      {
        "scope":"block",
        "action":"REWRITE",
        "ref":"b1",
        "summary":"3문장을 1문장으로 축약",
        "target_desc":"'배경' 섹션 내 블록",
        "status":"accepted",                      // ← 결정이 기록됨
        "block": { "type":"text","id":"b1","content":"요약된 문단" }
      }
    ]
  },
  { "type":"base", "role":"user", "content":"이제 결론도 비슷하게" }
]
```

→ 함께 보내는 `document`는 이미 `b1`이 "요약된 문단"인 상태. LLM은 "배경은 끝났고 결론 차례"로 이해한다.

### 시나리오 B — 제안 → 거절

> 제안을 거절하면 문서는 그대로, 히스토리에는 거절 기록만 남는다.

```jsonc
{
  "type":"interaction","role":"assistant","content":"표현을 더 단호하게 바꿔봤습니다.",
  "actions":[
    {
      "scope":"block","action":"REWRITE","ref":"b2",
      "summary":"완곡한 표현을 단정적 어조로",
      "target_desc":"'주장' 섹션 내 블록",
      "status":"declined",                        // ← 거절
      "block":{ "type":"text","id":"b2","content":"...반드시 ...이다." }
    }
  ]
}
```

→ `document`의 `b2`는 **원래 내용 그대로**. LLM은 "단호한 어조 제안은 거부됨 → 다시 제안하지 말 것"으로 해석한다.

### 시나리오 C — 직접 지시 (instructed)

> "그렇게 말고 이렇게" — 사용자가 제안을 손봐서 방향을 지정한다.

```jsonc
"actions":[
  {
    "scope":"block",
    "action":"REWRITE",
    "ref":"b1",
    "summary":"한 문장으로 축약",
    "target_desc":"'배경' 섹션 내 블록",
    "status":"instructed",
    "instruction":"줄이되 통계 수치는 남겨줘",      // ← 사용자의 직접 지시
    "block":{ "type":"text","id":"b1","content":"요약된 문단" }
  }
]
```

직렬화 결과:

```
  #1 [REWRITE] [b1] '배경' 섹션 내 블록 → 직접 지시("줄이되 통계 수치는 남겨줘")
      · 의도: 한 문장으로 축약
```

→ LLM은 다음 턴에서 "통계는 남기고 축약"으로 재편집한다.

### 시나리오 D — 여러 블록 + 혼합 액션

> 한 턴에 REWRITE · REPLACE · INSERT 가 섞여 나오고, 사용자가 개별로 결정한다.

```jsonc
"actions":[
  {
    "scope":"block",
    "action":"REWRITE",
    "ref":"b1",
    "status":"accepted",
    "summary":"도입 문장 다듬기",
    "target_desc":"'개요' 섹션 내 블록",
    "block":{ "type":"text","id":"b1","content":"새 도입" }
  },
  {
    "scope":"block",
    "action":"REPLACE",
    "ref":"b1",
    "status":"declined",
    "summary":"용어 통일: '모델'→'아키텍처'",
    "target_desc":"'개요' 섹션 내 블록",
    "source":"모델",
    "target":"아키텍처"
  },
  {
    "scope":"block",
    "action":"INSERT",
    "ref":"b1",
    "status":"accepted",
    "summary":"한계점 문단 추가",
    "target_desc":"'개요' 섹션 내 블록",
    "block":{ "type":"text","id":"bNEW","content":"다만 ... 한계가 있다." }
  }
]
```

- 같은 블록(`b1`)을 여러 action이 가리켜도 UUID라 모호하지 않다.
- `INSERT`의 `ref`는 **기준(앵커) 블록**, `block.id`는 새로 생성된 UUID(`bNEW`).
- 프론트는 수락된 것만(REWRITE·INSERT) 적용, REPLACE는 무시. 다음 턴 히스토리엔 셋 다 결정과 함께 남는다.

### 시나리오 E — 섹션 구조 변경 (outline scope)

> 블록 본문이 아니라 섹션 트리를 바꾼다.

```jsonc
"actions":[
  { "scope":"outline","action":"ADD","ref":"S2","title":"실험 설정","level":2,
    "summary":"실험 섹션 하위에 '실험 설정' 추가","target_desc":"'실험' 섹션","status":"accepted" },
  { "scope":"outline","action":"MERGE","targets":["S3","S4"],"ref":"S3",
    "summary":"중복된 두 결론 섹션 병합","target_desc":"'결론' 섹션","status":"pending" }
]
```

- `scope:"outline"` 은 `ref`가 **섹션 code**(블록 UUID 아님). ADD는 부모 섹션 code.
- 직렬화 시 `#1 [ADD] [S2] '실험' 섹션 → 수락` 처럼 블록 액션과 동일한 포맷으로 풀린다(`ref`엔 섹션 code).

### 시나리오 F — clarify (선택지 질문)

> 어시스턴트가 편집 대신 되묻고, 사용자가 보기를 고른다.

clarify(선택지 제시)와 option_reply(선택)는 각각 **전용 메시지 타입**이다 — `clarify_options`/
`picked_option_index` 는 base 메시지에 얹지 않고 자기 타입이 들고 있다.

```jsonc
// 서버 → 프론트 (type=clarify)
{ "type":"clarify","role":"assistant","content":"어떤 방향으로 줄일까요?",
  "clarify_options":["핵심만 1문장","절반 분량","불필요한 예시만 제거"] }

// 다음 턴, 프론트 → 서버 (사용자가 ②를 고름 → type=option_reply)
{ "type":"option_reply","role":"user","content":"절반 분량","picked_option_index":1 }
```

직렬화 (LLM 히스토리): **선택지 목록은 싣지 않고, 사용자가 고른 값만** 남긴다.
`clarify_options`/`picked_option_index` 는 프론트 렌더·리플레이용으로 wire 에만 있고 LLM엔 안 들어간다.

```
[ASSISTANT · 사용자에게 질문] 어떤 방향으로 줄일까요?
[USER] 절반 분량
```

→ LLM은 "질문에 대해 사용자가 '절반 분량'으로 답했다"로 해석한다. (보기 ①②③ 전체를 매번
히스토리에 쌓지 않아 토큰을 아끼고, 고른 결론만 명확히 전달된다.)

---

## 5. 누적 규칙 요약

- **결정은 직전 어시스턴트 턴에 되써진다.** user는 새 메시지를 추가하면서, 직전 제안 action들의 `status`(+필요시 `instruction`, `picked_option_index`)를 채워 보낸다.
- **수락된 변경은 `document`에 이미 반영돼 온다.** 히스토리의 action은 "왜/무엇을 했는지"의 기록이고, 실제 상태의 근거(source of truth)는 함께 오는 `document`다.
- **UUID는 히스토리의 키.** LLM 히스토리에도 블록 UUID를 `[uuid]`로 노출해, 문서 렌더(`[<uuid>] (type) content`)와 같은 키로 액션↔현재 블록을 결정적으로 연결한다. (토큰을 더 아끼려면 짧은 alias 도입을 검토할 수 있으나, 현재는 안정성을 위해 UUID 그대로 사용.)
- **응답 본문엔 태그/코드 금지.** `[ASSISTANT · …]`, `[제시된 문서 액션]`, 섹션 code, 블록 UUID는 히스토리 해석용일 뿐 — 사용자 화면엔 섹션 한국어 제목만 노출한다. (히스토리에서 UUID를 보더라도 응답엔 절대 흘리지 말 것.)

> 관련 코드: wire 스펙 `core/data/chat.py` · 문서 모델 `core/data/document.py` · 변환 `api/chat/serialize.py` · 히스토리 포맷 해설 `core/prompts.py::HISTORY_FORMAT_NOTE`.
