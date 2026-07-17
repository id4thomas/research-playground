from langgraph.graph import StateGraph, START, END

from agent.research.states import SubGraphState, SubGraphOutput
from agent.research.nodes.search_query_generator import search_query_generator_node
from agent.research.nodes.paper_searcher import paper_search_node
from agent.research.nodes.search_result_judge import judge_node
from agent.research.nodes.search_loop_condition import search_loop_condition_node
from agent.research.nodes.search_feedback_generator import generate_feedback_node
from agent.research.nodes.search_result_emitter import search_result_emitter_node


def build_search_subgraph():
    sg = StateGraph(SubGraphState, output=SubGraphOutput)

    sg.add_node("generate_query", search_query_generator_node)
    sg.add_node("search", paper_search_node)
    sg.add_node("judge", judge_node)
    sg.add_node("generate_feedback", generate_feedback_node)
    sg.add_node("emit", search_result_emitter_node)

    sg.add_edge(START, "generate_query")
    sg.add_edge("generate_query", "search")
    sg.add_edge("search", "judge")
    sg.add_conditional_edges("judge", search_loop_condition_node, {
        "generate_feedback": "generate_feedback",
        "emit": "emit",
    })
    sg.add_edge("generate_feedback", "generate_query")
    sg.add_edge("emit", END)

    return sg
