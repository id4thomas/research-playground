"""Clarify assemble node — converts clarify output into FinalOutput."""
from langchain_core.runnables import RunnableConfig

from agent.base import BaseNode
from agent.graphs.doc_assistant.states import AgentState, FinalOutput
from agent.operations import StripCodesOperation


class ClarifyAssembleNode(BaseNode):
    name = "clarify_assemble"

    async def run(self, state: AgentState, config: RunnableConfig) -> dict:
        out = state.get("clarify")
        doc = state["document"]
        msg = (out.question if out else None) or "어떤 부분을 도와드릴까요?"
        opts = list(out.options) if out else []
        return {
            "final": FinalOutput(
                message=await StripCodesOperation.run(msg, doc),
                clarify_options=[await StripCodesOperation.run(o, doc) for o in opts],
            )
        }


clarify_assemble_node = ClarifyAssembleNode()

__all__ = ["ClarifyAssembleNode", "clarify_assemble_node"]
