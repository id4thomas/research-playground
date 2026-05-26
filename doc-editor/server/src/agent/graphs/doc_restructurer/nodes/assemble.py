"""Restructure assemble node — converts restructure output into FinalOutput."""
from agent.graphs.doc_assistant.states import FinalOutput
from agent.modules.strip_codes import strip_section_codes
from agent.nodes.base import BaseNode


class RestructureAssembleNode(BaseNode):
    name = "restructure_assemble"

    async def run(self, state: dict) -> dict:
        out = state.get("restructure")
        doc = state["document"]
        message = strip_section_codes((out.message if out else "") or "", doc)
        return {
            "final": FinalOutput(
                message=message, outline_actions=out.actions if out else []
            )
        }


restructure_assemble_node = RestructureAssembleNode()

__all__ = ["RestructureAssembleNode", "restructure_assemble_node"]
