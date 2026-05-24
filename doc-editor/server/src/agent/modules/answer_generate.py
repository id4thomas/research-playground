"""Answer generation module — natural language reply."""
from langchain_core.messages import BaseMessage, SystemMessage
from pydantic import BaseModel

from core.langchain.llm import LangChainChatModel
from core.logger import get_logger
from core.data import Document

logger = get_logger(__name__)


class AnswerGenerateOutput(BaseModel):
    message: str = ""


_SYSTEM = """당신은 문서 편집 어시스턴트입니다. 사용자의 질문에 1~5문장으로 한국어로 답하세요.
- 문서 내용 기반 질문이면 outline과 대화 맥락을 활용.
- 'S1', 'S1-2;0' 같은 내부 코드를 노출하지 말고 섹션의 실제 한국어 제목으로 지칭.
"""


def _render_outline(document: Document) -> str:
    return "\n".join(
        f"{'  ' * (m.level - 1)}- {m.title}" for m in document.outline
    )


def _render_sections(document: Document, section_codes: list[str] | None) -> str:
    if not section_codes:
        return ""
    parts = []
    for code in section_codes:
        sec = document.sections.get(code)
        if not sec:
            continue
        parts.append(f"\n### {sec.meta.title}")
        for b in sec.blocks:
            parts.append(b.content)
    return "\n".join(parts)


async def generate_answer(
    messages: list[BaseMessage],
    document: Document,
    section_codes: list[str] | None = None,
) -> AnswerGenerateOutput:
    outline_text = _render_outline(document)
    body_text = _render_sections(document, section_codes)
    system_prompt = f"{_SYSTEM}\n\n## 문서 Outline\n{outline_text}"
    if body_text:
        system_prompt += f"\n\n## 참고 본문\n{body_text}"

    llm = LangChainChatModel.get_model(
        temperature=0.3,
        extra_body={"chat_template_kwargs": {"enable_thinking": False}},
    )
    try:
        result = await llm.ainvoke(
            [SystemMessage(content=system_prompt)] + list(messages)
        )
        message = result.content if hasattr(result, "content") else str(result)
    except Exception as e:
        logger.warning("[answer_generate] failed: %s", e)
        message = "답변 생성에 실패했습니다. 잠시 후 다시 시도해 주세요."
    logger.info("[answer_generate] %d chars", len(message))
    return AnswerGenerateOutput(message=message)
