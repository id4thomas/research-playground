"""Intent classification module — LLM call only, no LangGraph coupling.

이 모듈은 오직 intent 분기만 담당합니다. clarify 질문/보기는 별도의
`clarify_generate` 모듈(그리고 doc_clarifier 서브그래프)에서 생성합니다.
"""
from typing import Literal

from langchain_core.messages import BaseMessage, SystemMessage
from pydantic import BaseModel, Field

from core.langchain.llm import LangChainChatModel
from core.logger import get_logger
from core.data import Document

logger = get_logger(__name__)

INTENTS = ("edit", "restructure", "clarify", "answer")


class IntentClassifyOutput(BaseModel):
    intent: str = ""
    target_sections: list[str] = Field(default_factory=list)
    suggest_new_session: bool = False
    suggest_new_session_reason: str | None = None


class _LLMOut(BaseModel):
    intent: Literal["edit", "restructure", "clarify", "answer"]
    target_sections: list[str] = Field(default_factory=list)
    suggest_new_session: bool = False
    suggest_new_session_reason: str | None = None


_SYSTEM_BASE = """당신은 문서 편집 어시스턴트의 Intent Router입니다.
사용자 메시지와 문서 outline을 보고 아래 intent 중 하나만 선택하세요.
clarify 질문/보기는 다른 에이전트가 생성하므로, 여기서는 절대 생성하지 마세요.

- edit: 문서 블록의 본문을 직접 수정/추가/치환 해야할 경우
- restructure: 섹션의 이름, 계층 관련 추가/수정/삭제가 필요한 경우 (본문 변경 없음)
- clarify: 유저에게 추가적으로 선택을 받아야 하는 경우 (다지선다)
- answer: 수정 없이 질문에 답변하거나 설명을 요청한 경우

중요: 섹션 구조 변경과 본문 수정이 모두 필요해 보여도 restructure를 먼저 단독으로 추천하세요.
본문 수정은 사용자가 구조 변경을 수락한 다음 턴에서 별도로 처리됩니다.

target_sections: 수정 대상 섹션 코드 목록 (내부용 — 여기는 코드 그대로 사용).

selected가 비어있지 않으면 그 블록이 속한 섹션이 수정 대상이며 clarify로 분기하지 마세요.

★★★ 사용자에게 보여줄 텍스트(suggest_new_session_reason) 작성 규칙 ★★★

절대로 'S1', 'S1-1', 'S2-1-1', 'S1-1;0' 같은 내부 코드를 텍스트에 포함하지 마세요.
괄호로 묶어도 안 됩니다. 오직 섹션의 한국어 제목만 사용하세요.

❌ 금지 예시:
  - "S1-1 (종래 기술)의 내용을 더 구체화합니다."

✅ 권장 예시:
  - "'종래 기술' 섹션의 내용을 더 구체화합니다."
"""


async def classify_intent(
    messages: list[BaseMessage],
    document: Document,
    selected: list[str] | None,
) -> IntentClassifyOutput:
    outline_text = "\n".join(
        f"{'  ' * (m.level - 1)}{m.code}: {m.title}" for m in document.outline
    )
    selected_text = ", ".join(selected) if selected else "(없음)"
    system_prompt = (
        f"{_SYSTEM_BASE}\n\n"
        f"## 문서 Outline\n{outline_text}\n\n"
        f"## 선택된 블록\n{selected_text}"
    )
    llm = LangChainChatModel.get_model(
        temperature=0,
        extra_body={"chat_template_kwargs": {"enable_thinking": False}},
    ).with_structured_output(_LLMOut)
    try:
        result: _LLMOut = await llm.ainvoke(
            [SystemMessage(content=system_prompt)] + list(messages)
        )
    except Exception as e:
        logger.warning("[intent_classify] structured output failed: %s — fallback clarify", e)
        return IntentClassifyOutput(intent="clarify")
    logger.info("[intent_classify] intent=%s targets=%s", result.intent, result.target_sections)
    return IntentClassifyOutput(**result.model_dump())
