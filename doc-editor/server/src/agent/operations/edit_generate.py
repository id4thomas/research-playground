"""Edit generation operation — produce block-level edits via LLM."""
import copy

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


def _target_sections(document: Document, target_sections: list[str] | None):
    targets = set(target_sections) if target_sections is not None else set(document.sections.keys())
    return [(c, s) for c, s in document.sections.items() if c in targets]


def render_document(document: Document, target_sections: list[str] | None) -> str:
    """편집 대상 블록을 UUID와 함께 렌더한다.

    각 블록은 `[<block uuid>] (type:format) content` 형태로 표기되며, LLM은 수정 대상
    블록의 UUID를 그대로 `ref` 에 적는다 (ref enum 으로 유효 id만 허용됨). format 은
    콘텐츠 표현 방식(markdown/html/tex)으로, 재작성 시 같은 format 문법을 유지한다.
    """
    parts = []
    for code, section in _target_sections(document, target_sections):
        parts.append(f"\n### {section.meta.title} ({code})")
        for b in section.ordered_blocks():
            parts.append(f"[{b.id}] ({b.type}:{b.format}) {b.content}")
    return "\n".join(parts)


def collect_block_ids(document: Document, target_sections: list[str] | None) -> list[str]:
    """편집 가능한(렌더된) 블록 UUID 목록 — ref enum 제약에 사용."""
    ids: list[str] = []
    for _, section in _target_sections(document, target_sections):
        ids.extend(bid for bid in section.order if bid in section.blocks)
    return ids


def _schema_with_ref_enum(json_schema: dict | None, block_ids: list[str]) -> dict | None:
    """LLMEdit.ref 를 유효한 블록 UUID enum 으로 좁힌 schema 사본을 만든다.

    유효 id가 없으면(빈 섹션) 자유 문자열인 원본 schema를 그대로 쓴다.
    """
    if not json_schema or not block_ids:
        return json_schema
    schema = copy.deepcopy(json_schema)
    try:
        ref_prop = schema["$defs"]["LLMEdit"]["properties"]["ref"]
    except KeyError:
        return schema
    ref_prop.pop("anyOf", None)
    ref_prop["type"] = "string"
    ref_prop["enum"] = block_ids
    ref_prop["description"] = "수정 대상 블록의 UUID. 위 '문서 블록'에 표기된 id 중 하나만 사용."
    return schema


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
        base_schema = template.output_schema.json_schema if template.output_schema else None
        block_ids = collect_block_ids(document, target_sections)
        if selected:
            # 선택된 블록만 수정 가능 → enum 을 교집합으로 좁힌다.
            sel = set(selected)
            block_ids = [bid for bid in block_ids if bid in sel] or block_ids
        json_schema = _schema_with_ref_enum(base_schema, block_ids)
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
