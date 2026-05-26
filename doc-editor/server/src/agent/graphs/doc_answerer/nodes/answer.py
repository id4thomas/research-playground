"""Answer node — wraps answer_generate module."""
from agent.modules.answer_generate import AnswerGenerateOutput as AnswerOutput, generate_answer
from agent.nodes.base import BaseNode


class AnswerNode(BaseNode):
    name = "answer"

    async def run(self, state: dict) -> dict:
        ctx = state.get("context")
        section_codes = ctx.section_codes if ctx else None
        out = await generate_answer(
            messages=state["messages"],
            document=state["document"],
            section_codes=section_codes,
        )
        return {"answer": out}


answer_node = AnswerNode()

__all__ = ["AnswerNode", "AnswerOutput", "answer_node"]
