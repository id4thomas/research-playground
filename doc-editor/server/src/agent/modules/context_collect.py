"""Context collection module — pick which sections the action node should see.

Given a request + outline, asks the LLM to select section codes worth loading.
Output is a list of codes; downstream nodes only render those sections.
"""
from langchain_core.messages import BaseMessage, SystemMessage
from pydantic import BaseModel, Field

from core.langchain.llm import LangChainChatModel
from core.logger import get_logger
from core.data import Document

logger = get_logger(__name__)


class ContextCollectOutput(BaseModel):
    section_codes: list[str] = Field(default_factory=list)
    reasoning: str | None = None


class _LLMOut(BaseModel):
    section_codes: list[str] = Field(
        default_factory=list,
        description="이번 요청을 처리하기 위해 본문을 봐야 하는 섹션 코드 목록. outline에 존재하는 코드만 사용.",
    )
    reasoning: str | None = Field(
        default=None,
        description="간단한 이유 (디버깅용).",
    )


_SYSTEM = """당신은 문서 편집 어시스턴트의 컨텍스트 수집기입니다.
사용자 요청과 문서 outline을 보고, 후속 액션 노드가 실제 블록 내용을 봐야 할
섹션 코드 목록을 선정하세요.

규칙:
- outline에 존재하는 코드만 사용 (S1, S1-2, S2-1-1 등).
- 너무 많이 포함하면 비용이 커집니다. 정말 필요한 섹션만.
- 선택된 블록(selected)이 있으면 그 블록의 섹션은 반드시 포함.
- 직접 언급된 섹션 + 의미상 함께 봐야 하는 인접/참조 섹션 정도가 적절.
- 요청이 outline 전체에 대한 답변/구조 검토라면 모든 코드 반환 가능.
- 본문이 필요 없는 단순 질문이라면 빈 배열도 허용.
"""


async def collect_context(
    messages: list[BaseMessage],
    document: Document,
    selected: list[str] | None = None,
    hint_sections: list[str] | None = None,
) -> ContextCollectOutput:
    outline_text = "\n".join(
        f"{'  ' * (m.level - 1)}{m.code}: {m.title}" for m in document.outline
    )
    selected_text = ", ".join(selected) if selected else "(없음)"
    hint_text = ", ".join(hint_sections) if hint_sections else "(없음)"
    system_prompt = (
        f"{_SYSTEM}\n\n"
        f"## 문서 Outline\n{outline_text}\n\n"
        f"## 선택된 블록\n{selected_text}\n\n"
        f"## 인텐트 라우터의 후보 섹션 (참고)\n{hint_text}"
    )
    llm = LangChainChatModel.get_model(
        temperature=0,
        extra_body={"chat_template_kwargs": {"enable_thinking": False}},
    ).with_structured_output(_LLMOut)
    try:
        result: _LLMOut = await llm.ainvoke(
            [SystemMessage(content=system_prompt)] + list(messages)
        )
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
    logger.info("[context_collect] %d sections: %s", len(valid), valid)
    return ContextCollectOutput(section_codes=valid, reasoning=result.reasoning)
