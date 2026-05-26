"""Context collection module — pick which sections the action node should see.

Given a request + outline, asks the LLM to select section codes worth loading.
Output is a list of codes; downstream nodes only render those sections.
"""
from langchain_core.messages import BaseMessage, SystemMessage
from pydantic import BaseModel, Field

from core.langchain.llm import LangChainChatModel
from core.langchain.usage import TokenUsage
from core.logger import get_logger
from core.prompts import load_agent_spec
from core.data import Document

logger = get_logger(__name__)


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


async def collect_context(
    messages: list[BaseMessage],
    document: Document,
    selected: list[str] | None = None,
    hint_sections: list[str] | None = None,
) -> ContextCollectOutput:
    spec = load_agent_spec("context_collect")
    outline_text = "\n".join(
        f"{'  ' * (m.level - 1)}{m.code}: {m.title}" for m in document.outline
    )
    selected_text = ", ".join(selected) if selected else "(없음)"
    hint_text = ", ".join(hint_sections) if hint_sections else "(없음)"
    system_prompt = spec.render_system(
        outline_text=outline_text, selected_text=selected_text, hint_text=hint_text
    )
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
        logger.warning("[context_collect] failed: %s — fallback to hint/all", e)
        fallback = list(hint_sections or document.sections.keys())
        return ContextCollectOutput(section_codes=fallback, reasoning="fallback")

    valid = [c for c in result.section_codes if c in document.sections]
    if selected:
        sel_secs = {ref.split(";", 1)[0] for ref in selected}
        for s in sel_secs:
            if s in document.sections and s not in valid:
                valid.append(s)
    logger.info("[context_collect] %d sections: %s usage=%s", len(valid), valid, usage.model_dump())
    return ContextCollectOutput(section_codes=valid, reasoning=result.reasoning, token_usage=usage)
