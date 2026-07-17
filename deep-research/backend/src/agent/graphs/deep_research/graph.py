from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from agent.graphs.deep_research.state import DeepResearchState
from agent.graphs.deep_research.nodes.topic_generation import topic_generation_node
from agent.graphs.deep_research.nodes.search import search_node
from agent.graphs.deep_research.nodes.review import review_node
from agent.graphs.deep_research.nodes.aggregation import aggregation_node
from agent.graphs.deep_research.nodes.report import report_node


def should_continue(state: DeepResearchState) -> str:
    max_iteration = state.get("max_research_iteration", 2)
    if state.get("pending_topics") and state.get("research_iteration", 0) < max_iteration:
        return "search"
    return "finish"


def build_graph() -> CompiledStateGraph:
    b = StateGraph(DeepResearchState)

    # Nodes
    b.add_node("topic_generation", topic_generation_node)
    b.add_node("search", search_node)
    b.add_node("review", review_node)
    b.add_node("aggregation", aggregation_node)
    b.add_node("report", report_node)

    # Edges
    b.add_edge(START, "topic_generation")
    b.add_edge("topic_generation", "search")
    b.add_edge("search", "review")
    b.add_conditional_edges(
        "review",
        should_continue,
        {"search": "search", "finish": "aggregation"}
    )
    b.add_edge("aggregation", "report")
    b.add_edge("report", END)
    return b.compile()


graph = build_graph()
