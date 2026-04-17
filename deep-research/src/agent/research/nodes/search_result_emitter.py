from agent.research.states import SubGraphState, SubGraphResult
from core.logger import get_logger

logger = get_logger(__name__)

def search_result_emitter_node(state: SubGraphState) -> dict:
    result = SubGraphResult(
        topic=state.topic,
        papers=sorted(
            [p for p in state.papers if p.relevance_score >= state.score_threshold],
            key=lambda p: p.relevance_score,
            reverse=True,
        ),
    )
    logger.info("[emitter] Emitting %d papers for topic=%s", len(result.papers), state.topic)
    # Return as list for operator.add fan-in
    return {"subgraph_results": [result]}