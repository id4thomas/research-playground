"""Edit generation operation — produce block-level edits via LLM."""
from pydantic import BaseModel, Field

from agent.base import BaseLLMOperation, ChatMessage, format_history
from core.data import Document, LLMEdit
from core.langchain.usage import TokenUsage
from core.logger import get_logger

logger = get_logger(__name__)


class EditGenerateOutput(BaseModel):
    edits: list[LLMEdit] = Field(default_factory=list)
    message: str | None = None
    token_usage: TokenUsage = Field(default_factory=TokenUsage)


class _LLMOut(BaseModel):
    message: str = Field(
        description=(
            "사용자에게 보여줄 한국어 응답. 1~3문장. "
            "'S1', 'S1-2;0' 같은 코드를 노출하지 말고 섹션의 실제 한국어 제목으로 지칭."
        )
    )
    edits: list[LLMEdit] = Field(default_factory=list)


def render_document(document: Document, target_sections: list[str] | None) -> str:
    targets = set(target_sections) if target_sections is not None else set(document.sections.keys())
    parts = []
    for code, section in document.sections.items():
        if code not in targets:
            continue
        parts.append(f"\n### {section.meta.title} ({code})")
        for i, b in enumerate(section.blocks):
            parts.append(f"[{code};{i}] ({b.type}) {b.content}")
    return "\n".join(parts)


def _enforce_action_rules(edits: list[LLMEdit]) -> list[LLMEdit]:
    """ref당 REWRITE는 1개만. REWRITE가 있는 ref에는 다른 액션을 두지 않는다.

    LLM이 같은 블록에 대해 여러 REWRITE 후보를 나열하는 경향이 있어
    서버에서 첫 번째 REWRITE만 남기고 나머지를 버린다.
    """
    rewrite_seen: set[str] = set()
    out: list[LLMEdit] = []
    for e in edits:
        if e.action == "REWRITE":
            if e.ref in rewrite_seen:
                continue
            rewrite_seen.add(e.ref)
            out.append(e)
        else:
            out.append(e)
    return [e for e in out if not (e.action != "REWRITE" and e.ref in rewrite_seen)]


class EditGenerateOperation(BaseLLMOperation):
    PROMPT_NAME = "edit"

    @classmethod
    async def run(
        cls,
        instruction: str,
        document: Document,
        selected: list[str] | None = None,
        target_sections: list[str] | None = None,
        history: list[ChatMessage] | None = None,
    ) -> EditGenerateOutput:
        """Produce block-level edits for the document.

        Args:
            instruction: The user edit instruction to act on — the final turn.
                Injected into the prompt as `instruction`.
            document: Source doc whose block contents are rendered for editing.
            selected: Block codes the user highlighted — when set, only these
                blocks may be edited.
            target_sections: Section codes to render (e.g. from intent/context
                steps). `None` renders the whole document.
            history: Earlier chat turns, formatted into `history_text` as
                context only.
        """
        template = cls._load_prompt(cls.PROMPT_NAME)
        doc_text = render_document(document, target_sections)
        selected_ctx = ""
        if selected:
            selected_ctx = f"\n\n## 선택된 블록 (이 블록들만 수정)\n{', '.join(selected)}"
        messages = template.fill_template(
            {
                "doc_text": doc_text,
                "selected_ctx": selected_ctx,
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
            logger.warning("[edit_generate] structured output failed: %s", e)
            return EditGenerateOutput(
                edits=[],
                message="수정안을 생성하지 못했습니다. 요청 범위를 좁혀 다시 시도해 주세요.",
            )

        logger.info("[edit_generate] %d edit(s) proposed usage=%s", len(result.edits), usage.model_dump())
        deduped = _enforce_action_rules(result.edits)
        if len(deduped) != len(result.edits):
            logger.info(
                "[edit_generate] enforced action rules: %d → %d edit(s)",
                len(result.edits), len(deduped),
            )
        return EditGenerateOutput(edits=deduped, message=result.message, token_usage=usage)
