"""Intent classification module — LLM call only, no LangGraph coupling.

이 모듈은 오직 intent 분기만 담당합니다. clarify 질문/보기는 별도의
`clarify_generate` 모듈(그리고 doc_clarifier 서브그래프)에서 생성합니다.
"""
from typing import Literal

from langchain_core.messages import BaseMessage, SystemMessage
from pydantic import BaseModel, Field

from core.langchain.llm import LangChainChatModel
from core.langchain.usage import TokenUsage
from core.logger import get_logger
from core.prompts import load_agent_spec
from core.data import Document

logger = get_logger(__name__)

INTENTS = ("edit", "restructure", "clarify", "answer")


class IntentClassifyOutput(BaseModel):
    intent: str = ""
    target_sections: list[str] = Field(default_factory=list)
    suggest_new_session: bool = False
    suggest_new_session_reason: str | None = None
    token_usage: TokenUsage = Field(default_factory=TokenUsage)


class _LLMOut(BaseModel):
    intent: Literal["edit", "restructure", "clarify", "answer"]
    target_sections: list[str] = Field(default_factory=list)
    suggest_new_session: bool = False
    suggest_new_session_reason: str | None = None


async def classify_intent(
    messages: list[BaseMessage],
    document: Document,
    selected: list[str] | None,
) -> IntentClassifyOutput:
    spec = load_agent_spec("intent_classify")
    outline_text = "\n".join(
        f"{'  ' * (m.level - 1)}{m.code}: {m.title}" for m in document.outline
    )
    selected_text = ", ".join(selected) if selected else "(없음)"
    system_prompt = spec.render_system(outline_text=outline_text, selected_text=selected_text)
    llm = LangChainChatModel.get_model(**spec.model_kwargs).with_structured_output(
        spec.output_schema, include_raw=True
    )
    try:
        raw = await llm.ainvoke(
            [SystemMessage(content=system_prompt)] + list(messages)
        )
        result: _LLMOut = raw["parsed"]
        usage = TokenUsage.from_message(raw)
    except Exception as e:
        logger.warning("[intent_classify] structured output failed: %s — fallback clarify", e)
        return IntentClassifyOutput(intent="clarify")
    logger.info(
        "[intent_classify] intent=%s targets=%s usage=%s",
        result.intent, result.target_sections, usage.model_dump(),
    )
    return IntentClassifyOutput(**result.model_dump(), token_usage=usage)
