from typing import Literal

from agent.research.states import SubGraphState
from core.logger import get_logger

logger = get_logger(__name__)

def search_loop_condition_node(state: SubGraphState) -> Literal["generate_feedback", "emit"]:
    qualified = len(state.papers)
    decision = "emit" if qualified >= state.min_required or state.attempt >= state.max_attempts else "generate_feedback"
    logger.info("[search_loop_condition] topic=%s, qualified=%d, attempt=%d/%d -> %s", state.topic, qualified, state.attempt, state.max_attempts, decision)
    return decision
