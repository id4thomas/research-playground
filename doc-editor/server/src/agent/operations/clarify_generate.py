"""Clarify generation operation — produce a clarifying question + clickable options."""
from pydantic import BaseModel, Field

from agent.base import BaseLLMOperation, ChatMessage, format_history
from core.data import Document
from core.langchain.usage import TokenUsage
from core.logger import get_logger

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


class ClarifyGenerateOperation(BaseLLMOperation):
    PROMPT_NAME = "clarify"

    @classmethod
    async def run(
        cls,
        instruction: str,
        document: Document,
        selected: list[str] | None = None,
        history: list[ChatMessage] | None = None,
    ) -> ClarifyGenerateOutput:
        """Ask a clarifying question with clickable options for a vague request.

        Args:
            instruction: The ambiguous user instruction to clarify — the final
                turn. Injected into the prompt as `instruction`.
            document: Source doc; its outline is shown so options can reference
                real sections.
            selected: Section/block codes the user highlighted, if any —
                narrows what the question should be about.
            history: Earlier chat turns, formatted into `history_text` as
                context only.
        """
        template = cls._load_prompt(cls.PROMPT_NAME)
        outline_text = "\n".join(
            f"{'  ' * (m.level - 1)}{m.code}: {m.title}" for m in document.outline
        )
        selected_text = ", ".join(selected) if selected else "(없음)"
        messages = template.fill_template(
            {
                "outline_text": outline_text,
                "selected_text": selected_text,
                "history_text": format_history(history),
                "instruction": instruction,
            }
        )

        model = cls._load_model(template.generation_config)
        json_schema = template.output_schema.json_schema if template.output_schema else None
        try:
            msg = await cls.generate(model, messages, json_schema=json_schema)
            result = _LLMOut.model_validate_json(msg.content)
            usage = cls.parse_token_usage(msg)
        except Exception as e:
            logger.warning("[clarify_generate] structured output failed: %s", e)
            return ClarifyGenerateOutput(
                question="요청을 조금 더 구체적으로 알려주실 수 있을까요?",
                options=[],
            )

        logger.info("[clarify_generate] %d option(s) usage=%s", len(result.options), usage.model_dump())
        return ClarifyGenerateOutput(question=result.question, options=result.options, token_usage=usage)
