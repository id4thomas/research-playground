"""Answer generation module — natural language reply."""
from langchain_core.messages import BaseMessage, SystemMessage
from pydantic import BaseModel, Field

from core.langchain.llm import LangChainChatModel
from core.langchain.usage import TokenUsage
from core.logger import get_logger
from core.prompts import load_agent_spec
from core.data import Document

logger = get_logger(__name__)


class AnswerGenerateOutput(BaseModel):
    message: str = ""
    token_usage: TokenUsage = Field(default_factory=TokenUsage)


def _render_outline(document: Document) -> str:
    return "\n".join(
        f"{'  ' * (m.level - 1)}- {m.title}" for m in document.outline
    )


def _render_sections(document: Document, section_codes: list[str] | None) -> str:
    if not section_codes:
        return ""
    parts = []
    for code in section_codes:
        sec = document.sections.get(code)
        if not sec:
            continue
        parts.append(f"\n### {sec.meta.title}")
        for b in sec.blocks:
            parts.append(b.content)
    return "\n".join(parts)


async def generate_answer(
    messages: list[BaseMessage],
    document: Document,
    section_codes: list[str] | None = None,
) -> AnswerGenerateOutput:
    spec = load_agent_spec("answer")
    outline_text = _render_outline(document)
    body_text = _render_sections(document, section_codes)
    system_prompt = spec.render_system(outline_text=outline_text, body_text=body_text)

    llm = LangChainChatModel.get_model(**spec.model_kwargs)
    usage = TokenUsage()
    try:
        result = await llm.ainvoke(
            [SystemMessage(content=system_prompt)] + list(messages)
        )
        message = result.content if hasattr(result, "content") else str(result)
        usage = TokenUsage.from_message(result)
    except Exception as e:
        logger.warning("[answer_generate] failed: %s", e)
        message = "답변 생성에 실패했습니다. 잠시 후 다시 시도해 주세요."
    logger.info("[answer_generate] %d chars usage=%s", len(message), usage.model_dump())
    return AnswerGenerateOutput(message=message, token_usage=usage)
