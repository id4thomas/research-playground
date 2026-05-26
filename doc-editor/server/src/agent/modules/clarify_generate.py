"""Clarify generation module — produce a clarifying question + clickable options."""
from langchain_core.messages import BaseMessage, SystemMessage
from pydantic import BaseModel, Field

from core.langchain.llm import LangChainChatModel
from core.langchain.usage import TokenUsage
from core.logger import get_logger
from core.prompts import load_agent_spec
from core.data import Document

logger = get_logger(__name__)


class ClarifyGenerateOutput(BaseModel):
    question: str = ""
    options: list[str] = Field(default_factory=list)
    token_usage: TokenUsage = Field(default_factory=TokenUsage)


class _LLMOut(BaseModel):
    question: str = Field(
        description="사용자에게 보여줄 한국어 질문. 1~2문장. 모호한 요청을 좁히기 위한 질문."
    )
    options: list[str] = Field(
        default_factory=list,
        description=(
            "사용자가 클릭만으로 답할 수 있는 2~4개의 짧은 한국어 보기. "
            "각 항목은 그대로 후속 요청으로 사용된다."
        ),
    )


async def generate_clarify(
    messages: list[BaseMessage],
    document: Document,
    selected: list[str] | None = None,
) -> ClarifyGenerateOutput:
    spec = load_agent_spec("clarify")
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
        logger.warning("[clarify_generate] structured output failed: %s", e)
        return ClarifyGenerateOutput(
            question="요청을 조금 더 구체적으로 알려주실 수 있을까요?",
            options=[],
        )
    logger.info("[clarify_generate] %d option(s) usage=%s", len(result.options), usage.model_dump())
    return ClarifyGenerateOutput(question=result.question, options=result.options, token_usage=usage)
