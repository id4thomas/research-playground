from langchain_core.runnables import RunnableConfig

from agent.base import BaseNode
from agent.operations.research_review import ResearchReviewOperation

from agent.graphs.deep_research.state import DeepResearchState


class ReviewNode(BaseNode):
    """수집 결과를 검토하고 추가로 탐색할 토픽을 생성"""

    name = "review"

    async def run(self, state: DeepResearchState, config: RunnableConfig) -> dict:
        # RunnableConfig로 주입
        client = config["configurable"]["openai_client"]

        result = await ResearchReviewOperation.run(
            client=client,
            instruction=state["instruction"],
            topics=state.get("topics", []),
            retrieved=state.get("retrieved", []),
            max_topics=state.get("n_topics", 3),
        )

        followups = [] if result.sufficient else result.followup_topics
        # 이미 탐색한 토픽은 제외
        explored = set(state.get("topics", []))
        followups = [t for t in followups if t not in explored]

        return {"review": result.review, "pending_topics": followups}


review_node = ReviewNode()

__all__ = ["ReviewNode", "review_node"]
