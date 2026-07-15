from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from agent.graphs.deep_research_alt.state import DeepResearchAltState
from agent.graphs.deep_research_alt.nodes.supervisor import supervisor_node

# 집계/보고서 노드는 deep_research와 동일하게 동작하므로 재사용
from agent.graphs.deep_research.nodes.aggregation import aggregation_node
from agent.graphs.deep_research.nodes.report import report_node


def build_graph() -> CompiledStateGraph:
    b = StateGraph(DeepResearchAltState)

    # Nodes
    # supervisor는 create_agent 서브그래프라 tool calling 루프를 내부에서 수행
    b.add_node("supervisor", supervisor_node)
    b.add_node("aggregation", aggregation_node)
    b.add_node("report", report_node)

    # Edges
    b.add_edge(START, "supervisor")
    b.add_edge("supervisor", "aggregation")
    b.add_edge("aggregation", "report")
    b.add_edge("report", END)
    return b.compile()


graph = build_graph()
