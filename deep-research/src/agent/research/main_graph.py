from langchain_core.runnables import RunnableConfig
from langgraph.types import Send
from langgraph.graph import StateGraph, START, END
from langgraph.graph.state import CompiledStateGraph

from core.logger import get_logger

logger = get_logger(__name__)

from agent.base import BaseAgent
from agent.research.states import ResearchState, PaperData, SearchConfig
from agent.research.nodes.topic_generator import topic_generator_node
from agent.research.search_subgraph import build_search_subgraph


def fan_out_by_topic(state: ResearchState, config: RunnableConfig) -> list[Send]:
    logger.info("[fan_out] Distributing %d topics to subgraphs", len(state.topics))
    cfg = SearchConfig(**config.get("configurable", {}).get("search", {}))
    return [
        Send("search_subgraph", {
            "user_query": state.query,
            "topic": topic,
            "max_attempts": cfg.max_attempts,
            "search_limit": cfg.search_limit,
            "min_required": cfg.min_required,
            "score_threshold": cfg.score_threshold,
        })
        for topic in state.topics
    ]


async def collect_and_rank(state: ResearchState) -> dict:
    logger.info("[collect_and_rank] Collecting results from %d subgraphs", len(state.subgraph_results))
    all_papers: list[PaperData] = []
    seen: set[str] = set()

    for batch in state.subgraph_results:
        top_in_topic = sorted(
            batch.papers, key=lambda p: p.relevance_score, reverse=True
        )[:state.top_k_per_topic]

        for paper in top_in_topic:
            if paper.id not in seen:
                all_papers.append(paper)
                seen.add(paper.id)

    all_papers.sort(key=lambda p: p.relevance_score, reverse=True)
    return {"result": all_papers[:state.top_k]}


class ResearchAgent(BaseAgent):
    _name = "ResearchAgent"

    def compile_graph(self) -> CompiledStateGraph:
        builder = StateGraph(ResearchState)

        builder.add_node("generate_topics", topic_generator_node)
        builder.add_node("search_subgraph", build_search_subgraph().compile())
        builder.add_node("collect_and_rank", collect_and_rank)

        builder.add_edge(START, "generate_topics")
        builder.add_conditional_edges(
            "generate_topics", fan_out_by_topic, ["search_subgraph"]
        )
        builder.add_edge("search_subgraph", "collect_and_rank")
        builder.add_edge("collect_and_rank", END)

        return builder.compile()

    async def invoke(self, state: dict, config: SearchConfig | None = None) -> dict:
        graph = self.compile_graph()
        run_config = {"configurable": {"search": (config or SearchConfig()).model_dump()}}
        return await graph.ainvoke(state, config=run_config)

    async def astream(self, state: dict, config: SearchConfig | None = None):
        graph = self.compile_graph()
        run_config = {"configurable": {"search": (config or SearchConfig()).model_dump()}}
        async for event in graph.astream_events(state, config=run_config, version="v2"):
            yield event
