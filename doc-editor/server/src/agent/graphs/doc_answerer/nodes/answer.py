"""Answer node — wraps AnswerGenerateOperation."""
from langchain_core.runnables import RunnableConfig

from agent.base import BaseNode, split_instruction_history
from agent.graphs.doc_answerer.states import AnswererState
from agent.operations import AnswerGenerateOperation


class AnswerNode(BaseNode):
    name = "answer"

    async def run(self, state: AnswererState, config: RunnableConfig) -> dict:
        instruction, history = split_instruction_history(state["messages"])
        ctx = state.get("context")
        section_codes = ctx.section_codes if ctx else None
        out = await AnswerGenerateOperation.run(
            instruction=instruction,
            document=state["document"],
            section_codes=section_codes,
            history=history,
        )
        return {"answer": out}


answer_node = AnswerNode()

__all__ = ["AnswerNode", "answer_node"]
