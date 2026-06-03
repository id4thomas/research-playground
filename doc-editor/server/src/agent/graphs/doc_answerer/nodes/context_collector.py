"""Context collector node — selects which sections to load before answering."""
from langchain_core.runnables import RunnableConfig

from agent.base import BaseNode, split_instruction_history
from agent.graphs.doc_answerer.states import AnswererState
from agent.operations import ContextCollectOperation, ContextCollectOutput


class ContextCollectorNode(BaseNode):
    name = "context_collector"

    async def run(self, state: AnswererState, config: RunnableConfig) -> dict:
        instruction, history = split_instruction_history(state["messages"])
        hint = state.get("hint_sections")
        out = await ContextCollectOperation.run(
            instruction=instruction,
            document=state["document"],
            selected=state.get("selected"),
            hint_sections=hint,
            history=history,
        )
        return {"context": out}

    def on_error(self, state: AnswererState, err: Exception) -> dict:
        return {"context": ContextCollectOutput(section_codes=[], reasoning="error")}


context_collector_node = ContextCollectorNode()

__all__ = ["ContextCollectorNode", "context_collector_node"]
