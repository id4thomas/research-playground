"""Intent classification operation — LLM call only, no LangGraph coupling.

오직 intent 분기만 담당합니다. clarify 질문/보기는 별도의 ClarifyGenerateOperation
(그리고 doc_clarifier 서브그래프)에서 생성합니다.
"""
from typing import Literal

from pydantic import BaseModel, Field

from agent.base import BaseLLMOperation, ChatMessage, format_history
from core.data import Document
from core.langchain.usage import TokenUsage
from core.logger import get_logger

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


class IntentClassifyOperation(BaseLLMOperation):
    PROMPT_NAME = "intent_classify"

    @classmethod
    async def run(
        cls,
        instruction: str,
        document: Document,
        selected: list[str] | None = None,
        history: list[ChatMessage] | None = None,
    ) -> IntentClassifyOutput:
        """Decide which intent `instruction` maps to.

        Args:
            instruction: The user instruction being classified — the final turn.
                Injected into the prompt as `instruction` so the template frames
                the intent analysis around it.
            document: Source doc — its outline is shown so the model can pick
                `target_sections` and judge whether the request is in scope.
            selected: Section/block codes the user explicitly highlighted in
                the editor, if any. Narrows what the request likely refers to.
            history: Earlier chat turns, formatted into `history_text` as
                context only. The classification target is `instruction`.
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
            logger.warning("[intent_classify] structured output failed: %s — fallback clarify", e)
            return IntentClassifyOutput(intent="clarify")

        logger.info(
            "[intent_classify] intent=%s targets=%s usage=%s",
            result.intent, result.target_sections, usage.model_dump(),
        )
        return IntentClassifyOutput(**result.model_dump(), token_usage=usage)
