from agent.research.states import PaperData, SubGraphState
from client.huggingface import (
    HuggingfacePapersClient,
    Paper as HFPaper
)
from core.logger import get_logger

logger = get_logger(__name__)

async def search_papers(query: str, limit: int = 3) -> list[HFPaper]:
    search_client = HuggingfacePapersClient()
    hf_papers: list[HFPaper] = await search_client.search(query, limit=limit)
    return hf_papers

async def paper_search_node(state: SubGraphState) -> dict:
    """HuggingFace Papers API로 실제 검색"""
    logger.info("[paper_searcher] Searching query=%s, topic=%s, attempt=%d", state.search_query, state.topic, state.attempt)
    search_query=state.search_query
    hf_papers = await search_papers(
        query=search_query,
        limit=state.search_limit
    )
    
    # Process to PaperData
    topic = state.topic
    user_query = state.user_query
    new_papers = [
        PaperData(
            id=paper.id,
            title=paper.title,
            summary=paper.summary,
            authors=[a.name for a in paper.authors],
            relevance_score=0.0,  # 점수 초기화
            source_topic=topic,
            source_query=search_query,
        )
        for paper in hf_papers
    ]
    
    # Merge with Previous results
    seen = {p.id for p in state.papers}
    merged = list(state.papers)
    for p in new_papers:
        if p.id and p.id not in seen:
            merged.append(p)
            seen.add(p.id)
            
    logger.info("[paper_searcher] Found %d new papers, %d total after merge", len(new_papers), len(merged))
    return {"papers": merged, "attempt": state.attempt + 1}
