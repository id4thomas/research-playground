"""Shared context collector node — usable by any agent graph."""
from agent.modules.context_collect import ContextCollectOutput, collect_context
from agent.nodes.base import BaseNode


class ContextCollectorNode(BaseNode):
    name = "context_collector"

    async def run(self, state: dict) -> dict:
        orch = state.get("intent_router")
        hint = orch.target_sections if orch else None
        out = await collect_context(
            messages=state["messages"],
            document=state["document"],
            selected=state.get("selected"),
            hint_sections=hint,
        )
        return {"context": out}

    def on_error(self, state: dict, err: Exception) -> dict:
        return {"context": ContextCollectOutput(section_codes=[], reasoning="error")}


context_collector_node = ContextCollectorNode()

__all__ = ["ContextCollectorNode", "context_collector_node"]
