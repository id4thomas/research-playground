"""doc_assistant — single-pass graph composing per-intent subgraphs.

START → intent_router → (route) → one of:
  - edit_agent         (doc_editor subgraph)
  - restructure_agent  (doc_restructurer subgraph)
  - answer_agent       (doc_answerer subgraph)
  - clarify_agent      (doc_clarifier subgraph)
→ END

각 서브그래프는 자체적으로 `final` (FinalOutput)을 부모 상태에 쓴다. doc_assistant는
오직 intent 분류 + 라우팅만 담당한다.
"""
from langgraph.graph import StateGraph, START, END
from langgraph.graph.state import CompiledStateGraph

from agent.base import BaseAgent
from agent.graphs.doc_answerer.graph import build_answerer_graph
from agent.graphs.doc_assistant.nodes.intent_router import intent_router_node
from agent.graphs.doc_assistant.states import AgentState
from agent.graphs.doc_clarifier.graph import build_clarifier_graph
from agent.graphs.doc_editor.graph import build_editor_graph
from agent.graphs.doc_restructurer.graph import build_restructurer_graph


def _route_after_intent(state: dict) -> str:
    orch = state.get("intent_router")
    if not orch:
        return "clarify_agent"
    if orch.intent == "edit":
        return "edit_agent"
    if orch.intent == "restructure":
        return "restructure_agent"
    if orch.intent == "answer":
        return "answer_agent"
    return "clarify_agent"


class DocAssistantAgent(BaseAgent):
    _name = "DocAssistantAgent"

    def __init__(self) -> None:
        self._graph: CompiledStateGraph | None = None

    def compile_graph(self) -> CompiledStateGraph:
        if self._graph is not None:
            return self._graph

        b = StateGraph(AgentState)
        b.add_node("intent_router", intent_router_node)
        b.add_node("edit_agent", build_editor_graph())
        b.add_node("restructure_agent", build_restructurer_graph())
        b.add_node("answer_agent", build_answerer_graph())
        b.add_node("clarify_agent", build_clarifier_graph())

        b.add_edge(START, "intent_router")
        b.add_conditional_edges(
            "intent_router",
            _route_after_intent,
            {
                "edit_agent": "edit_agent",
                "restructure_agent": "restructure_agent",
                "answer_agent": "answer_agent",
                "clarify_agent": "clarify_agent",
            },
        )
        b.add_edge("edit_agent", END)
        b.add_edge("restructure_agent", END)
        b.add_edge("answer_agent", END)
        b.add_edge("clarify_agent", END)

        self._graph = b.compile()
        return self._graph

    async def invoke(self, state: dict) -> dict:
        return await self.compile_graph().ainvoke(state)
