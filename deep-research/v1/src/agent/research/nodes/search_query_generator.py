import json
from typing import Optional
from pydantic import BaseModel

from agent.research.states import SubGraphState
from core.llm.langchain import LangChainChatModel
from core.logger import get_logger

logger = get_logger(__name__)

MODEL_NAME = "Qwen3.5-35B-A3B"

class QueryResponse(BaseModel):
    """검색 쿼리"""
    query: str
    
    
# Prompt (Temporary)
INSTRUCTION_TEMPLATE = """학술 논문 검색 쿼리를 1개 생성하세요.
유저 요청사항: {user_query}
검색 탐색 방향: {topic}

{feedback}

규칙:
- HuggingFace Papers에서 검색할 영어 쿼리
- 간결하고 핵심 키워드 중심 (3~6 단어)

다음 JSON 형식으로 출력합니다
{{"query": str}}"""

async def generate_search_query(
    topic: str,
    user_query: str,
    feedback: Optional[str]=None
) -> str:
    if feedback:
        feedback_contents = f"추가 피드백: {feedback}"
    else:
        feedback_contents = ""
    
    instruction = INSTRUCTION_TEMPLATE.format(
        topic=topic,
        user_query=user_query,
        feedback=feedback_contents
    )
    messages = [
        {"role": "user", "content": instruction}
    ]
    response = await LangChainChatModel.chat(messages, model_name=MODEL_NAME, response_format=QueryResponse)
    query = json.loads(response.content)["query"]
    return query

async def search_query_generator_node(state: SubGraphState) -> dict:
    logger.info("[search_query_generator] topic=%s, attempt=%d", state.topic, state.attempt)
    query = await generate_search_query(
        topic=state.topic,
        user_query=state.user_query,
        feedback=state.feedback
    )
    logger.info("[search_query_generator] Generated query: %s", query)
    return {"search_query": query}
