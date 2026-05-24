"""Clarify generation module — produce a clarifying question + clickable options."""
from langchain_core.messages import BaseMessage, SystemMessage
from pydantic import BaseModel, Field

from core.langchain.llm import LangChainChatModel
from core.logger import get_logger
from core.data import Document

logger = get_logger(__name__)


class ClarifyGenerateOutput(BaseModel):
    question: str = ""
    options: list[str] = Field(default_factory=list)


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


_SYSTEM = """당신은 문서 편집 어시스턴트의 Clarify 에이전트입니다.
사용자의 요청이 모호하여 다음 행동을 결정할 수 없을 때, 사용자가 빠르게 선택해
답할 수 있는 짧은 질문과 2~4개의 클릭 가능한 보기를 한국어로 생성하세요.

★★★ 사용자에게 보여줄 텍스트(question, options) 작성 규칙 ★★★

절대로 'S1', 'S1-1', 'S2-1-1', 'S1-1;0' 같은 내부 코드를 텍스트에 포함하지 마세요.
괄호로 묶어도 안 됩니다. 오직 섹션의 한국어 제목만 사용하세요.

❌ 금지 예시:
  - "S1-1 (종래 기술)의 내용을 더 구체화합니다."

✅ 권장 예시:
  - "'종래 기술' 섹션의 내용을 더 구체화합니다."

동음이의 섹션이 있어 제목만으로 구분이 어려우면 상위 섹션 제목으로 한정하세요.
예: "'해결 수단' 아래의 '핵심 구성' 섹션"

options는 사용자가 그대로 다음 발화로 사용할 수 있는 자연스러운 한국어 문장으로 작성하세요.
"""


async def generate_clarify(
    messages: list[BaseMessage],
    document: Document,
    selected: list[str] | None = None,
) -> ClarifyGenerateOutput:
    outline_text = "\n".join(
        f"{'  ' * (m.level - 1)}{m.code}: {m.title}" for m in document.outline
    )
    selected_text = ", ".join(selected) if selected else "(없음)"
    system_prompt = (
        f"{_SYSTEM}\n\n"
        f"## 문서 Outline\n{outline_text}\n\n"
        f"## 선택된 블록\n{selected_text}"
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
        logger.warning("[clarify_generate] structured output failed: %s", e)
        return ClarifyGenerateOutput(
            question="요청을 조금 더 구체적으로 알려주실 수 있을까요?",
            options=[],
        )
    logger.info("[clarify_generate] %d option(s)", len(result.options))
    return ClarifyGenerateOutput(question=result.question, options=result.options)
