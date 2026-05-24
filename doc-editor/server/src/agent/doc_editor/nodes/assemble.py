"""Edit assemble node — converts edit_generate output into FinalOutput."""
from agent.doc_assistant.states import FinalOutput
from agent.modules.edit_assemble import edits_to_map
from agent.modules.strip_codes import strip_section_codes
from agent.nodes.base import BaseNode


class EditAssembleNode(BaseNode):
    name = "edit_assemble"

    async def run(self, state: dict) -> dict:
        edit_out = state.get("edit")
        doc = state["document"]
        edits_map = edits_to_map(edit_out.edits) if edit_out else {}
        message = strip_section_codes((edit_out.message if edit_out else "") or "", doc)
        return {"final": FinalOutput(message=message, edits=edits_map)}


edit_assemble_node = EditAssembleNode()

__all__ = ["EditAssembleNode", "edit_assemble_node"]
