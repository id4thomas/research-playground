import json
from pydantic import BaseModel

from agent.research.states import ResearchState
from core.llm.langchain import LangChainChatModel
from core.logger import get_logger

logger = get_logger(__name__)

MODEL_NAME = "Qwen3.5-35B-A3B"

class TopicsResponse(BaseModel):
    """탐색 방향의 주제들"""
    topics: list[str]
    
    
# Prompt (Temporary)
INSTRUCTION_TEMPLATE = """사용자의 연구 주제에 대해 서로 다른 검색 방향(토픽)을 {n}개 제시하세요.
각 토픽은 해당 주제를 탐구할 수 있는 독립적인 관점이어야 합니다.

사용자 쿼리: {query}

다음 JSON 형식으로 출력합니다
{{"topic": list[str]}}"""

async def generate_topics(query: str, n: int = 3) -> list[str]:
    instruction = INSTRUCTION_TEMPLATE.format(
        query=query,
        n=n
    )
    messages = [
        {"role": "user", "content": instruction}
    ]
    response = await LangChainChatModel.chat(messages, model_name=MODEL_NAME, response_format=TopicsResponse)
    topics = json.loads(response.content)["topics"]
    return topics

async def topic_generator_node(state: ResearchState) -> dict:
    logger.info("[topic_generator] Generating %d topics for query: %s", state.num_topics, state.query)
    n = state.num_topics
    query = state.query
    topics = await generate_topics(query,n=n)
    logger.info("[topic_generator] Generated topics: %s", topics)
    return {"topics": topics}