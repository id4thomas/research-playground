"""Edit generation module — produce block-level edits via LLM."""
from langchain_core.messages import BaseMessage, SystemMessage
from pydantic import BaseModel, Field

from core.langchain.llm import LangChainChatModel
from core.langchain.usage import TokenUsage
from core.logger import get_logger
from core.prompts import load_agent_spec
from core.data import Document, LLMEdit

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


async def generate_edits(
    messages: list[BaseMessage],
    document: Document,
    selected: list[str] | None = None,
    target_sections: list[str] | None = None,
) -> EditGenerateOutput:
    spec = load_agent_spec("edit")
    doc_text = render_document(document, target_sections)
    selected_ctx = ""
    if selected:
        selected_ctx = f"\n\n## 선택된 블록 (이 블록들만 수정)\n{', '.join(selected)}"
    system_prompt = spec.render_system(doc_text=doc_text, selected_ctx=selected_ctx)

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
    # REWRITE가 채택된 ref에서는 REPLACE/INSERT 제거
    return [e for e in out if not (e.action != "REWRITE" and e.ref in rewrite_seen)]
