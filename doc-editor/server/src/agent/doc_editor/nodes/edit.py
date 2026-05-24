"""Edit node — wraps edit_generate module."""
from agent.modules.edit_generate import EditGenerateOutput as EditOutput, generate_edits
from agent.nodes.base import BaseNode


class EditNode(BaseNode):
    name = "edit"

    async def run(self, state: dict) -> dict:
        orch = state.get("intent_router")
        ctx = state.get("context")
        target = None
        if ctx and getattr(ctx, "section_codes", None):
            target = ctx.section_codes
        elif orch and orch.target_sections:
            target = orch.target_sections
        out = await generate_edits(
            messages=state["messages"],
            document=state["document"],
            selected=state.get("selected"),
            target_sections=target,
        )
        return {"edit": out}


edit_node = EditNode()

__all__ = ["EditNode", "EditOutput", "edit_node"]
