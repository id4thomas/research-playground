"""Intent router node — wraps IntentClassifyOperation."""
from langchain_core.runnables import RunnableConfig

from agent.base import BaseNode, split_instruction_history
from agent.graphs.doc_assistant.states import AgentState
from agent.operations import IntentClassifyOperation, IntentClassifyOutput


class IntentRouterNode(BaseNode):
    name = "intent_router"

    async def run(self, state: AgentState, config: RunnableConfig) -> dict:
        instruction, history = split_instruction_history(state["messages"])
        out = await IntentClassifyOperation.run(
            instruction=instruction,
            document=state["document"],
            selected=state.get("selected"),
            history=history,
        )
        return {"intent_router": out}

    def on_error(self, state: AgentState, err: Exception) -> dict:
        return {"intent_router": IntentClassifyOutput(intent="clarify")}


intent_router_node = IntentRouterNode()


def route_by_intent(state: AgentState) -> str:
    orch = state.get("intent_router")
    return orch.intent if orch else "clarify"


__all__ = ["IntentRouterNode", "intent_router_node", "route_by_intent"]
