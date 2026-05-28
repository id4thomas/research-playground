"""Answer assemble node — converts answer output into FinalOutput."""
from langchain_core.runnables import RunnableConfig

from agent.base import BaseNode
from agent.graphs.doc_assistant.states import AgentState, FinalOutput
from agent.operations import StripCodesOperation


class AnswerAssembleNode(BaseNode):
    name = "answer_assemble"

    async def run(self, state: AgentState, config: RunnableConfig) -> dict:
        out = state.get("answer")
        doc = state["document"]
        message = await StripCodesOperation.run((out.message if out else "") or "", doc)
        return {"final": FinalOutput(message=message)}


answer_assemble_node = AnswerAssembleNode()

__all__ = ["AnswerAssembleNode", "answer_assemble_node"]
