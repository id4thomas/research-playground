from langchain_core.runnables import RunnableConfig

from agent.base import BaseNode
from agent.operations.hf_paper_search import HFPaperSearchOperation
from agent.graphs.hf_paper_search.state import SearchState

class SearchNode(BaseNode):
    name = "search"
    
    async def run(self, state: SearchState, config: RunnableConfig) -> dict:
        # RunnableConfig로 주입
        client = config["configurable"]["hf_client"] 
        
        query = state["query"]
        limit = state["option"].search_limit
        
        result = await HFPaperSearchOperation.run(
            client=client,
            query=query,
            limit=limit
        )
        state["retrieved"] = result
        return state
    
search_node = SearchNode()

__all__ = ["SearchNode", "search_node"]