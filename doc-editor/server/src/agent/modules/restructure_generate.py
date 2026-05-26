"""Restructure generation module — outline-level (section tree) actions."""
from langchain_core.messages import BaseMessage, SystemMessage
from pydantic import BaseModel, Field

from core.langchain.llm import LangChainChatModel
from core.langchain.usage import TokenUsage
from core.logger import get_logger
from core.prompts import load_agent_spec
from core.data import Document, OutlineAction

logger = get_logger(__name__)


class RestructureGenerateOutput(BaseModel):
    actions: list[OutlineAction] = Field(default_factory=list)
    message: str | None = None
    token_usage: TokenUsage = Field(default_factory=TokenUsage)


class _LLMOut(BaseModel):
    message: str = Field(
        description=(
            "사용자에게 보여줄 한국어 응답. 어떤 섹션 변경을 왜 제안했는지 1~3문장. "
            "'S1', 'S1-2' 같은 내부 코드를 노출하지 말고 섹션 제목으로 지칭."
        )
    )
    outline_actions: list[OutlineAction] = Field(default_factory=list)


def _render_outline(document: Document) -> str:
    return "\n".join(
        f"{'  ' * (m.level - 1)}{m.code} (level={m.level}): {m.title}"
        for m in document.outline
    )


async def generate_restructure(
    messages: list[BaseMessage],
    document: Document,
) -> RestructureGenerateOutput:
    spec = load_agent_spec("restructure")
    outline_text = _render_outline(document)
    system_prompt = spec.render_system(outline_text=outline_text)
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
        logger.warning("[restructure_generate] structured output failed: %s", e)
        return RestructureGenerateOutput(
            actions=[],
            message=(
                "섹션 구조 변경 요청을 해석하지 못했습니다. 어떤 섹션을 어떻게 바꾸고 싶은지 "
                "조금 더 구체적으로 알려주세요."
            ),
        )
    logger.info(
        "[restructure_generate] %d action(s): %s usage=%s",
        len(result.outline_actions),
        [a.action for a in result.outline_actions],
        usage.model_dump(),
    )
    return RestructureGenerateOutput(
        actions=result.outline_actions, message=result.message, token_usage=usage
    )
