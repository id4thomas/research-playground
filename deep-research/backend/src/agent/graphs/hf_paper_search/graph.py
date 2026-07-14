from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from agent.graphs.hf_paper_search.state import SearchState
from agent.graphs.hf_paper_search.nodes.search import search_node
from agent.graphs.hf_paper_search.nodes.query_generation import query_generation_node
from agent.graphs.hf_paper_search.nodes.judge import judge_node


def should_continue(state: SearchState) -> str:
    option = state["option"]
    if len(state.get("final", [])) >= option.min_required:
        return "end"
    if state.get("iteration", 0) >= option.max_iteration:
        return "end"
    return "retry"


def build_graph() -> CompiledStateGraph:
    b = StateGraph(SearchState)

    # Nodes
    b.add_node("search", search_node)
    b.add_node("query_generation", query_generation_node)
    b.add_node("judge", judge_node)

    # Edges
    b.add_edge(START, "query_generation")
    b.add_edge("query_generation", "search")
    b.add_edge("search", "judge")
    b.add_conditional_edges(
        "judge",
        should_continue,
        {"retry": "query_generation", "end": END}
    )
    return b.compile()


graph = build_graph()
