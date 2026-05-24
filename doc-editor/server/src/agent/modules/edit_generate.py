"""Edit generation module — produce block-level edits via LLM."""
from langchain_core.messages import BaseMessage, SystemMessage
from pydantic import BaseModel, Field

from core.langchain.llm import LangChainChatModel
from core.logger import get_logger
from core.data import Document, LLMEdit

logger = get_logger(__name__)


class EditGenerateOutput(BaseModel):
    edits: list[LLMEdit] = Field(default_factory=list)
    message: str | None = None


class _LLMOut(BaseModel):
    message: str = Field(
        description=(
            "사용자에게 보여줄 한국어 응답. 1~3문장. "
            "'S1', 'S1-2;0' 같은 코드를 노출하지 말고 섹션의 실제 한국어 제목으로 지칭."
        )
    )
    edits: list[LLMEdit] = Field(default_factory=list)


_SYSTEM = """당신은 범용 문서 편집 어시스턴트입니다.
문서 섹션(블록 목록)과 사용자 요청을 보고 블록 단위 수정안을 JSON으로 생성합니다.

블록 ref 형식: "<섹션코드>;<블록인덱스>"  예) "S1;0", "S1-2;3"
- ref 필드에서는 위 코드를 그대로 사용.

액션: REWRITE (블록 전체 재작성) | REPLACE (substring 치환) | INSERT (아래에 삽입)

★★★ 블록당 액션 개수 규칙 ★★★
- REWRITE: 같은 블록(ref)에 대해 **반드시 1개만** 제안합니다. 여러 버전의 재작성안을 나열하지 마세요. 가장 적합한 단일 안을 고르세요.
- REPLACE: 같은 블록에 대해 서로 다른 substring을 치환하는 경우에 한해 N개 허용.
- INSERT: 같은 블록 아래 N개 삽입 허용.
- 같은 ref에 REWRITE와 REPLACE/INSERT를 섞지 마세요. REWRITE를 선택했다면 그 블록에는 REWRITE 1개만 둡니다.

★★★ message(사용자에게 보여줄 응답) 작성 규칙 ★★★
절대로 'S1', 'S1-1', 'S1-2;0' 같은 내부 코드를 포함하지 마세요. 괄호로 묶어도 안 됩니다.
오직 섹션의 한국어 제목만 사용하세요.

❌ 금지: "S1-2 (문제점) 섹션의 첫 번째 블록을 보완했습니다."
✅ 권장: "'문제점' 섹션의 첫 번째 부분을 보완했습니다."

미사용 필드는 반드시 null. 코드블록 없이 순수 JSON만 반환합니다."""


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
    doc_text = render_document(document, target_sections)
    selected_ctx = ""
    if selected:
        selected_ctx = f"\n\n## 선택된 블록 (이 블록들만 수정)\n{', '.join(selected)}"
    system_prompt = (
        f"{_SYSTEM}\n\n"
        f"## 문서 블록\n{doc_text}{selected_ctx}"
    )

    llm = LangChainChatModel.get_model(
        temperature=0.2,
        extra_body={"chat_template_kwargs": {"enable_thinking": False}},
    ).with_structured_output(_LLMOut)
    try:
        result: _LLMOut = await llm.ainvoke(
            [SystemMessage(content=system_prompt)] + list(messages)
        )
    except Exception as e:
        logger.warning("[edit_generate] structured output failed: %s", e)
        return EditGenerateOutput(
            edits=[],
            message="수정안을 생성하지 못했습니다. 요청 범위를 좁혀 다시 시도해 주세요.",
        )
    logger.info("[edit_generate] %d edit(s) proposed", len(result.edits))
    deduped = _enforce_action_rules(result.edits)
    if len(deduped) != len(result.edits):
        logger.info(
            "[edit_generate] enforced action rules: %d → %d edit(s)",
            len(result.edits), len(deduped),
        )
    return EditGenerateOutput(edits=deduped, message=result.message)


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
