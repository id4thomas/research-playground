"""Context collector node — selects which sections to load before answering."""
from langchain_core.runnables import RunnableConfig

from agent.base import BaseNode, split_instruction_history
from agent.graphs.doc_assistant.states import AgentState
from agent.operations import ContextCollectOperation, ContextCollectOutput


class ContextCollectorNode(BaseNode):
    name = "context_collector"

    async def run(self, state: AgentState, config: RunnableConfig) -> dict:
        instruction, history = split_instruction_history(state["messages"])
        orch = state.get("intent_router")
        hint = orch.target_sections if orch else None
        out = await ContextCollectOperation.run(
            instruction=instruction,
            document=state["document"],
            selected=state.get("selected"),
            hint_sections=hint,
            history=history,
        )
        return {"context": out}

    def on_error(self, state: AgentState, err: Exception) -> dict:
        return {"context": ContextCollectOutput(section_codes=[], reasoning="error")}


context_collector_node = ContextCollectorNode()

__all__ = ["ContextCollectorNode", "context_collector_node"]
