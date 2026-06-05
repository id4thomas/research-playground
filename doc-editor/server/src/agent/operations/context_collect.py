"""Context collection operation — pick which sections the action node should see.

Given a request + outline, asks the LLM to select section codes worth loading.
Output is a list of codes; downstream nodes only render those sections.
"""
from pydantic import BaseModel, Field

from agent.base import BaseLLMOperation, ChatMessage, format_history
from core.data import Document
from core.langchain.usage import TokenUsage
from core.logger import get_logger

logger = get_logger(__name__)

# 후속 노드 토큰 사용량을 제한하기 위한 상한 (prompt/schema 의 maxItems 와 일치).
MAX_SECTION_CODES = 20


class ContextCollectOutput(BaseModel):
    section_codes: list[str] = Field(default_factory=list)
    reasoning: str | None = None
    token_usage: TokenUsage = Field(default_factory=TokenUsage)


class _LLMOut(BaseModel):
    section_codes: list[str] = Field(
        default_factory=list,
        description="이번 요청을 처리하기 위해 본문을 봐야 하는 섹션 코드 목록. outline에 존재하는 코드만 사용.",
    )
    reasoning: str | None = Field(
        default=None,
        description="간단한 이유 (디버깅용).",
    )


class ContextCollectOperation(BaseLLMOperation):
    PROMPT_NAME = "context_collect"

    @classmethod
    async def run(
        cls,
        instruction: str,
        document: Document,
        selected: list[str] | None = None,
        hint_sections: list[str] | None = None,
        history: list[ChatMessage] | None = None,
    ) -> ContextCollectOutput:
        """Select which section codes downstream nodes should load.

        Args:
            instruction: The user instruction whose relevant sections we're
                picking — the final turn. Injected into the prompt as
                `instruction`.
            document: Source doc; only its outline is shown (the point is to
                decide which bodies to load later).
            selected: Section/block codes the user highlighted — their sections
                are always force-included in the result.
            hint_sections: Candidate sections from an earlier step (e.g. intent
                targets); used as a prior and as the fallback on failure.
            history: Earlier chat turns, formatted into `history_text` as
                context only.
        """
        template = cls._load_prompt(cls.PROMPT_NAME)
        outline_text = "\n".join(
            f"{'  ' * (m.level - 1)}{m.code}: {m.title}" for m in document.outline
        )
        selected_text = ", ".join(selected) if selected else "(없음)"
        hint_text = ", ".join(hint_sections) if hint_sections else "(없음)"
        messages = template.fill_template(
            {
                "outline_text": outline_text,
                "selected_text": selected_text,
                "hint_text": hint_text,
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
            logger.warning("[context_collect] failed: %s — fallback to hint/all", e)
            fallback = list(hint_sections or document.sections.keys())
            return ContextCollectOutput(section_codes=fallback, reasoning="fallback")

        valid = [c for c in result.section_codes if c in document.sections]
        if len(valid) > MAX_SECTION_CODES:
            logger.warning(
                "[context_collect] %d sections > cap %d — truncating",
                len(valid), MAX_SECTION_CODES,
            )
            valid = valid[:MAX_SECTION_CODES]
        if selected:
            # selected 는 블록 UUID 목록 → 소속 섹션을 강제 포함.
            for ref in selected:
                sec, _ = document.find_block(ref)
                if sec and sec.meta.code not in valid:
                    valid.append(sec.meta.code)
        logger.info("[context_collect] %d sections: %s usage=%s", len(valid), valid, usage.model_dump())
        return ContextCollectOutput(section_codes=valid, reasoning=result.reasoning, token_usage=usage)
