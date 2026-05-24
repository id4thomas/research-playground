"""Clarify node — wraps clarify_generate module."""
from agent.modules.clarify_generate import ClarifyGenerateOutput, generate_clarify
from agent.nodes.base import BaseNode


class ClarifyNode(BaseNode):
    name = "clarify"

    async def run(self, state: dict) -> dict:
        out = await generate_clarify(
            messages=state["messages"],
            document=state["document"],
            selected=state.get("selected"),
        )
        return {"clarify": out}

    def on_error(self, state: dict, err: Exception) -> dict:
        return {
            "clarify": ClarifyGenerateOutput(
                question="요청을 해석하지 못했습니다. 조금 더 구체적으로 말씀해 주세요.",
                options=[],
            )
        }


clarify_node = ClarifyNode()

__all__ = ["ClarifyNode", "ClarifyGenerateOutput", "clarify_node"]
