from langchain_core.runnables import RunnableConfig

from agent.base import BaseNode
from agent.operations.topic_generation import TopicGenerationOperation

from agent.graphs.deep_research.state import DeepResearchState


class TopicGenerationNode(BaseNode):
    name = "topic_generation"

    async def run(self, state: DeepResearchState, config: RunnableConfig) -> dict:
        # RunnableConfig로 주입
        client = config["configurable"]["openai_client"]

        topics = await TopicGenerationOperation.run(
            client=client,
            instruction=state["instruction"],
            n=state.get("n_topics", 3),
        )
        return {"pending_topics": topics}


topic_generation_node = TopicGenerationNode()

__all__ = ["TopicGenerationNode", "topic_generation_node"]
