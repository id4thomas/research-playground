"""Clarify node — wraps ClarifyGenerateOperation."""
from langchain_core.runnables import RunnableConfig

from agent.base import BaseNode, split_instruction_history
from agent.graphs.doc_clarifier.states import ClarifierState
from agent.operations import ClarifyGenerateOperation, ClarifyGenerateOutput


class ClarifyNode(BaseNode):
    name = "clarify"

    async def run(self, state: ClarifierState, config: RunnableConfig) -> dict:
        instruction, history = split_instruction_history(state["messages"])
        out = await ClarifyGenerateOperation.run(
            instruction=instruction,
            document=state["document"],
            selected=state.get("selected"),
            history=history,
        )
        return {"clarify": out}

    def on_error(self, state: ClarifierState, err: Exception) -> dict:
        return {
            "clarify": ClarifyGenerateOutput(
                question="요청을 해석하지 못했습니다. 조금 더 구체적으로 말씀해 주세요.",
                options=[],
            )
        }


clarify_node = ClarifyNode()

__all__ = ["ClarifyNode", "clarify_node"]
