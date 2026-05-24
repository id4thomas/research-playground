"""Intent router node — wraps intent_classify module for the doc_assistant graph."""
from agent.modules.intent_classify import (
    IntentClassifyOutput as IntentRouterOutput,
    classify_intent,
)
from agent.nodes.base import BaseNode


class IntentRouterNode(BaseNode):
    name = "intent_router"

    async def run(self, state: dict) -> dict:
        out = await classify_intent(
            messages=state["messages"],
            document=state["document"],
            selected=state.get("selected"),
        )
        return {"intent_router": out}

    def on_error(self, state: dict, err: Exception) -> dict:
        return {"intent_router": IntentRouterOutput(intent="clarify")}


intent_router_node = IntentRouterNode()


def route_by_intent(state: dict) -> str:
    orch = state.get("intent_router")
    return orch.intent if orch else "clarify"


__all__ = ["IntentRouterNode", "IntentRouterOutput", "intent_router_node", "route_by_intent"]
