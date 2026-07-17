import asyncio

from langchain_core.runnables import RunnableConfig
from langgraph.config import get_stream_writer

from agent.base import BaseNode
from agent.data.paper import PaperRetrievalData
from agent.data.search_option import SearchOption
from agent.graphs.hf_paper_search.graph import graph as search_graph

from agent.graphs.deep_research.state import DeepResearchState


class SearchNode(BaseNode):
    """pending_topics 각각에 대해 hf_paper_search 그래프를 서브에이전트로 병렬 실행"""

    name = "search"

    async def run(self, state: DeepResearchState, config: RunnableConfig) -> dict:
        option = state.get("option") or SearchOption()
        pending = state.get("pending_topics", [])
        # stream_mode="custom" 사용 시 토픽별 진행상황 emit (비스트리밍 실행에서는 no-op)
        writer = get_stream_writer()

        async def run_subagent(topic: str) -> list[PaperRetrievalData]:
            writer({"type": "search_start", "topic": topic})
            # config를 그대로 넘겨 hf_client/openai_client가 서브그래프에 주입되도록 함
            result = await search_graph.ainvoke({"topic": topic, "option": option}, config)
            final = result.get("final", [])
            writer({
                "type": "search_done",
                "topic": topic,
                "n_papers": len(final),
                "iteration": result.get("iteration", 0),
            })
            return final

        results = await asyncio.gather(*[run_subagent(topic) for topic in pending])

        retrieved: list[PaperRetrievalData] = []
        for final in results:
            retrieved.extend(final)

        return {
            "retrieved": retrieved,
            "topics": pending,
            "pending_topics": [],
            "research_iteration": state.get("research_iteration", 0) + 1,
        }


search_node = SearchNode()

__all__ = ["SearchNode", "search_node"]
