"""Restructure generation module — outline-level (section tree) actions."""
from langchain_core.messages import BaseMessage, SystemMessage
from pydantic import BaseModel, Field

from core.langchain.llm import LangChainChatModel
from core.logger import get_logger
from core.data import Document, OutlineAction

logger = get_logger(__name__)


class RestructureGenerateOutput(BaseModel):
    actions: list[OutlineAction] = Field(default_factory=list)
    message: str | None = None


class _LLMOut(BaseModel):
    message: str = Field(
        description=(
            "사용자에게 보여줄 한국어 응답. 어떤 섹션 변경을 왜 제안했는지 1~3문장. "
            "'S1', 'S1-2' 같은 내부 코드를 노출하지 말고 섹션 제목으로 지칭."
        )
    )
    outline_actions: list[OutlineAction] = Field(default_factory=list)


_SYSTEM = """당신은 문서의 섹션 구조(헤더 트리)를 편집하는 에이전트입니다.
현재 outline을 보고 RENAME / ADD / REMOVE / MERGE 네 가지 액션을 JSON으로 생성하세요.

- RENAME: target=대상 섹션 코드, title=새 제목
- ADD:    target=부모 섹션 코드(루트면 null), title=새 제목, level=헤더 레벨(부모.level+1, 루트는 1), position=형제 중 0-based 위치(null=맨 뒤)
- REMOVE: target=대상 섹션 코드. 해당 섹션과 그 안의 모든 블록·하위 섹션이 함께 삭제됩니다. ★본문 손실★
- MERGE:  targets=합칠 섹션 코드 목록(outline 순서상 연속). 첫 번째가 생존, 나머지 블록이 뒤에 이어붙음. 본문 보존.

규칙:
- 본문 보존이 필요하면 MERGE 사용, REMOVE는 본문까지 삭제됨.
- ADD로 만든 섹션은 본문이 비어 있음 (본문 작성은 별도 턴).
- 미사용 필드는 null. 코드블록 없이 순수 JSON.
- 액션 불필요 시 outline_actions 빈 배열.

★★★ message(사용자에게 보여줄 응답) 작성 규칙 ★★★
절대로 'S1', 'S1-1', 'S2-1-1' 같은 내부 코드를 포함하지 마세요. 괄호로 묶어도 안 됩니다.
오직 섹션의 한국어 제목만 사용하세요.

❌ 금지: "S2-1 (핵심 구성) 아래에 S2-1-3 섹션을 추가합니다."
✅ 권장: "'핵심 구성' 섹션 아래에 '확장 모듈' 섹션을 추가합니다."
"""


def _render_outline(document: Document) -> str:
    return "\n".join(
        f"{'  ' * (m.level - 1)}{m.code} (level={m.level}): {m.title}"
        for m in document.outline
    )


async def generate_restructure(
    messages: list[BaseMessage],
    document: Document,
) -> RestructureGenerateOutput:
    outline_text = _render_outline(document)
    system_prompt = (
        f"{_SYSTEM}\n\n"
        f"## 현재 Outline\n{outline_text}"
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
        logger.warning("[restructure_generate] structured output failed: %s", e)
        return RestructureGenerateOutput(
            actions=[],
            message=(
                "섹션 구조 변경 요청을 해석하지 못했습니다. 어떤 섹션을 어떻게 바꾸고 싶은지 "
                "조금 더 구체적으로 알려주세요."
            ),
        )
    logger.info(
        "[restructure_generate] %d action(s): %s",
        len(result.outline_actions),
        [a.action for a in result.outline_actions],
    )
    return RestructureGenerateOutput(actions=result.outline_actions, message=result.message)
