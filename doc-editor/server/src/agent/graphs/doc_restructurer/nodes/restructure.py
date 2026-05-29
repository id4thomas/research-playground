"""Restructure node — wraps RestructureGenerateOperation."""
from langchain_core.runnables import RunnableConfig

from agent.base import BaseNode, split_instruction_history
from agent.graphs.doc_restructurer.states import RestructurerState
from agent.operations import RestructureGenerateOperation


class RestructureNode(BaseNode):
    name = "restructure"

    async def run(self, state: RestructurerState, config: RunnableConfig) -> dict:
        instruction, history = split_instruction_history(state["messages"])
        out = await RestructureGenerateOperation.run(
            instruction=instruction,
            document=state["document"],
            history=history,
        )
        return {"restructure": out}


restructure_node = RestructureNode()

__all__ = ["RestructureNode", "restructure_node"]
