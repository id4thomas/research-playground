"""Restructure assemble node — converts restructure output into FinalOutput."""
from langchain_core.runnables import RunnableConfig

from agent.base import BaseNode
from agent.graphs.doc_assistant.states import AgentState, FinalOutput
from agent.operations import StripCodesOperation


class RestructureAssembleNode(BaseNode):
    name = "restructure_assemble"

    async def run(self, state: AgentState, config: RunnableConfig) -> dict:
        out = state.get("restructure")
        doc = state["document"]
        message = await StripCodesOperation.run((out.message if out else "") or "", doc)
        return {
            "final": FinalOutput(
                message=message, outline_actions=out.actions if out else []
            )
        }


restructure_assemble_node = RestructureAssembleNode()

__all__ = ["RestructureAssembleNode", "restructure_assemble_node"]
