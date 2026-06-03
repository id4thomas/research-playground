"""Edit assemble node — converts edit output into FinalOutput."""
from langchain_core.runnables import RunnableConfig

from agent.base import BaseNode
from agent.graphs.doc_assistant.states import FinalOutput
from agent.graphs.doc_editor.states import EditorState
from agent.operations import EditAssembleOperation, StripCodesOperation


class EditAssembleNode(BaseNode):
    name = "edit_assemble"

    async def run(self, state: EditorState, config: RunnableConfig) -> dict:
        edit_out = state.get("edit")
        doc = state["document"]
        edits_map = await EditAssembleOperation.run(edit_out.edits) if edit_out else {}
        message = await StripCodesOperation.run((edit_out.message if edit_out else "") or "", doc)
        return {"final": FinalOutput(message=message, edits=edits_map)}


edit_assemble_node = EditAssembleNode()

__all__ = ["EditAssembleNode", "edit_assemble_node"]
