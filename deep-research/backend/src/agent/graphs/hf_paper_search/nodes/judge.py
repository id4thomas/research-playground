import asyncio

from langchain_core.runnables import RunnableConfig

from agent.base import BaseNode
from agent.data.paper import PaperRetrievalData
from agent.operations.retrieval_judge import RetrievalJudgeOperation

from agent.graphs.hf_paper_search.state import SearchState

class JudgeNode(BaseNode):
    name = "judge"

    async def run(self, state: SearchState, config: RunnableConfig) -> dict:
        # RunnableConfig로 주입
        client = config["configurable"]["openai_client"]

        topic = state["topic"]
        query = state["query"]
        retrieved = state.get("retrieved", [])
        threshold = state["option"].score_threshold

        final = state.get("final", [])

        # 이전 iteration에서 이미 수집된 논문은 제외
        seen_ids = {r.data.id for r in final}
        candidates = [p for p in retrieved if p.id not in seen_ids]

        scores = await asyncio.gather(*[
            RetrievalJudgeOperation.run(
                client=client,
                topic=topic,
                query=query,
                paper=paper
            )
            for paper in candidates
        ])

        for paper, score in zip(candidates, scores):
            if score < threshold:
                continue
            final.append(
                PaperRetrievalData(
                    data=paper,
                    score=score,
                    source_query=query,
                    source_topic=topic
                )
            )

        state["final"] = final
        state["iteration"] = state.get("iteration", 0) + 1
        return state

judge_node = JudgeNode()

__all__ = ["JudgeNode", "judge_node"]
