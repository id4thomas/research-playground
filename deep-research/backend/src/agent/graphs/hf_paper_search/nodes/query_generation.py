from langchain_core.runnables import RunnableConfig

from agent.base import BaseNode
from agent.operations.query_generation import QueryGenerationOperation

from agent.graphs.hf_paper_search.state import SearchState

class QueryGenerationNode(BaseNode):
    name = "query_generation"
    
    async def run(self, state: SearchState, config: RunnableConfig) -> dict:
        # RunnableConfig로 주입
        client = config["configurable"]["openai_client"] 
        
        topic = state["topic"]
        query = await QueryGenerationOperation.run(
            client=client,
            topic=topic
        )
        state["query"] = query
        return state
    
query_generation_node = QueryGenerationNode()

__all__ = ["QueryGenerationNode", "query_generation_node"]