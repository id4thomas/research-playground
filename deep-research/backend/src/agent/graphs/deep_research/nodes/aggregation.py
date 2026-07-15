from langchain_core.runnables import RunnableConfig

from agent.base import BaseNode
from agent.data.paper import PaperRetrievalData
from agent.data.result import TopicRetrievalResult

from agent.graphs.deep_research.state import DeepResearchState


class AggregationNode(BaseNode):
    """서브에이전트 final 결과들을 토픽별 TopicRetrievalResult로 집계"""

    name = "aggregation"

    async def run(self, state: DeepResearchState, config: RunnableConfig) -> dict:
        retrieved = state.get("retrieved", [])

        by_topic: dict[str, list[PaperRetrievalData]] = {}
        # 생성된 토픽 순서 유지 (검색 결과가 없는 토픽도 포함)
        for topic in state.get("topics", []):
            by_topic[topic] = []
        for r in retrieved:
            by_topic.setdefault(r.source_topic, []).append(r)

        results = [
            TopicRetrievalResult(topic=topic, result=papers)
            for topic, papers in by_topic.items()
        ]
        return {"results": results}


aggregation_node = AggregationNode()

__all__ = ["AggregationNode", "aggregation_node"]
