"""Restructure node — wraps restructure_generate module."""
from agent.modules.restructure_generate import (
    RestructureGenerateOutput as RestructureOutput,
    generate_restructure,
)
from agent.nodes.base import BaseNode


class RestructureNode(BaseNode):
    name = "restructure"

    async def run(self, state: dict) -> dict:
        out = await generate_restructure(
            messages=state["messages"], document=state["document"]
        )
        return {"restructure": out}


restructure_node = RestructureNode()

__all__ = ["RestructureNode", "RestructureOutput", "restructure_node"]
