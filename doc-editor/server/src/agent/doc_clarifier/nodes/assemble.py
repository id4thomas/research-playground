"""Clarify assemble node — converts clarify output into FinalOutput."""
from agent.doc_assistant.states import FinalOutput
from agent.modules.strip_codes import strip_section_codes
from agent.nodes.base import BaseNode


class ClarifyAssembleNode(BaseNode):
    name = "clarify_assemble"

    async def run(self, state: dict) -> dict:
        out = state.get("clarify")
        doc = state["document"]
        msg = (out.question if out else None) or "어떤 부분을 도와드릴까요?"
        opts = list(out.options) if out else []
        return {
            "final": FinalOutput(
                message=strip_section_codes(msg, doc),
                clarify_options=[strip_section_codes(o, doc) for o in opts],
            )
        }


clarify_assemble_node = ClarifyAssembleNode()

__all__ = ["ClarifyAssembleNode", "clarify_assemble_node"]
