"""Answer generation operation — natural language reply."""
from pydantic import BaseModel, Field

from agent.base import BaseLLMOperation, ChatMessage, format_history
from core.data import Document
from core.langchain.usage import TokenUsage
from core.logger import get_logger

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


class AnswerGenerateOperation(BaseLLMOperation):
    PROMPT_NAME = "answer"

    @classmethod
    async def run(
        cls,
        instruction: str,
        document: Document,
        section_codes: list[str] | None = None,
        history: list[ChatMessage] | None = None,
    ) -> AnswerGenerateOutput:
        """Write a natural-language reply to the user's question.

        Args:
            instruction: The user question to answer — the final turn. Injected
                into the prompt as `instruction`.
            document: Source doc; its outline is always shown for grounding.
            section_codes: Sections whose body text to include as evidence.
                Empty/`None` answers from the outline alone.
            history: Earlier chat turns, formatted into `history_text` as
                context only.
        """
        template = cls._load_prompt(cls.PROMPT_NAME)
        outline_text = _render_outline(document)
        body_text = _render_sections(document, section_codes)
        messages = template.fill_template(
            {
                "outline_text": outline_text,
                "body_text": body_text,
                "history_text": format_history(history),
                "instruction": instruction,
            }
        )

        model = cls._load_model(template.generation_config)
        usage = TokenUsage()
        try:
            msg = await cls.generate(model, messages)
            message = msg.content if hasattr(msg, "content") else str(msg)
            usage = cls.parse_token_usage(msg)
        except Exception as e:
            logger.warning("[answer_generate] failed: %s", e)
            message = "답변 생성에 실패했습니다. 잠시 후 다시 시도해 주세요."

        logger.info("[answer_generate] %d chars usage=%s", len(message), usage.model_dump())
        return AnswerGenerateOutput(message=message, token_usage=usage)
