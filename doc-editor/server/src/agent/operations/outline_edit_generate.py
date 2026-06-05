"""Outline edit generation operation — outline-level (section tree) actions."""
from pydantic import BaseModel, Field

from agent.base import BaseLLMOperation, ChatMessage, format_history
from core.data import Document, OutlineEdit
from core.langchain.usage import TokenUsage
from core.logger import get_logger

logger = get_logger(__name__)


class OutlineEditGenerateOutput(BaseModel):
    edits: list[OutlineEdit] = Field(default_factory=list)
    message: str | None = None
    token_usage: TokenUsage = Field(default_factory=TokenUsage)


class _LLMOut(BaseModel):
    message: str = Field(
        description=(
            "사용자에게 보여줄 한국어 응답. 어떤 섹션 변경을 왜 제안했는지 1~3문장. "
            "'S1', 'S1-2' 같은 내부 코드를 노출하지 말고 섹션 제목으로 지칭."
        )
    )
    outline_actions: list[OutlineEdit] = Field(default_factory=list)


def _render_outline(document: Document) -> str:
    return "\n".join(
        f"{'  ' * (m.level - 1)}{m.code} (level={m.level}): {m.title}"
        for m in document.outline
    )


class OutlineEditGenerateOperation(BaseLLMOperation):
    PROMPT_NAME = "restructure"

    @classmethod
    async def run(
        cls,
        instruction: str,
        document: Document,
        history: list[ChatMessage] | None = None,
    ) -> OutlineEditGenerateOutput:
        """Propose outline-level (section tree) actions.

        Args:
            instruction: The user restructure instruction to act on — the final
                turn. Injected into the prompt as `instruction`.
            document: Source doc whose outline (codes, levels, titles) is the
                tree being reorganized.
            history: Earlier chat turns, formatted into `history_text` as
                context only.
        """
        template = cls._load_prompt(cls.PROMPT_NAME)
        outline_text = _render_outline(document)
        messages = template.fill_template(
            {
                "outline_text": outline_text,
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
            logger.warning("[outline_edit_generate] structured output failed: %s", e)
            return OutlineEditGenerateOutput(
                edits=[],
                message=(
                    "섹션 구조 변경 요청을 해석하지 못했습니다. 어떤 섹션을 어떻게 바꾸고 싶은지 "
                    "조금 더 구체적으로 알려주세요."
                ),
            )

        logger.info(
            "[outline_edit_generate] %d action(s): %s usage=%s",
            len(result.outline_actions),
            [a.action for a in result.outline_actions],
            usage.model_dump(),
        )
        return OutlineEditGenerateOutput(
            edits=result.outline_actions, message=result.message, token_usage=usage
        )
