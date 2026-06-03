"""Edit node — wraps EditGenerateOperation."""
from langchain_core.runnables import RunnableConfig

from agent.base import BaseNode, split_instruction_history
from agent.graphs.doc_editor.states import EditorState
from agent.operations import EditGenerateOperation


class EditNode(BaseNode):
    name = "edit"

    async def run(self, state: EditorState, config: RunnableConfig) -> dict:
        instruction, history = split_instruction_history(state["messages"])
        ctx = state.get("context")
        target = None
        if ctx and getattr(ctx, "section_codes", None):
            target = ctx.section_codes
        else:
            target = state.get("hint_sections")
        out = await EditGenerateOperation.run(
            instruction=instruction,
            document=state["document"],
            selected=state.get("selected"),
            target_sections=target,
            history=history,
        )
        return {"edit": out}


edit_node = EditNode()

__all__ = ["EditNode", "edit_node"]
