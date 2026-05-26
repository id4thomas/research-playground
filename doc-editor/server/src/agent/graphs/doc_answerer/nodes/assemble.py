"""Answer assemble node — converts answer output into FinalOutput."""
from agent.graphs.doc_assistant.states import FinalOutput
from agent.modules.strip_codes import strip_section_codes
from agent.nodes.base import BaseNode


class AnswerAssembleNode(BaseNode):
    name = "answer_assemble"

    async def run(self, state: dict) -> dict:
        out = state.get("answer")
        doc = state["document"]
        message = strip_section_codes((out.message if out else "") or "", doc)
        return {"final": FinalOutput(message=message)}


answer_assemble_node = AnswerAssembleNode()

__all__ = ["AnswerAssembleNode", "answer_assemble_node"]
