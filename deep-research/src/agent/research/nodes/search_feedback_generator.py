import json
from typing import Optional
from pydantic import BaseModel, Field

from agent.research.states import PaperData, SubGraphState
from core.llm.langchain import LangChainChatModel
from core.logger import get_logger

logger = get_logger(__name__)

MODEL_NAME = "Qwen3.5-35B-A3B"

class FeedbackResponse(BaseModel):
    feedback: str = Field(description="다음 검색에서 보완할 방향")

INSTRUCTION_TEMPLATE = """현재 검색 결과가 부족합니다. 다음 검색에서 어떤 방향을 보완해야 하는지 피드백을 작성하세요.

유저 요청사항: {user_query}
검색 탐색 방향: {topic}

현재 확보된 논문 목록:
{paper_info}

한두 문장으로 구체적인 보완 방향을 제시하세요.

다음 JSON 형식으로 반환합니다
{{"feedback": str}}"""


async def generate_feedback(
    papers: list[PaperData],
    user_query: str,
    topic: str,
    max_summary_len: int = 256
) -> str:
    paper_info = [
        {
            "id": p.id,
            "title": p.title,
            "summary": p.summary[:max_summary_len]
        }
        for p in papers
    ]
    instruction = INSTRUCTION_TEMPLATE.format(
        user_query=user_query,
        topic=topic,
        paper_info=json.dumps(paper_info, ensure_ascii=False)
    )
    messages = [
        {"role": "user", "content": instruction}
    ]
    response = await LangChainChatModel.chat(messages, model_name=MODEL_NAME, response_format=FeedbackResponse)
    feedback = json.loads(response.content)["feedback"]
    return feedback

async def generate_feedback_node(state: SubGraphState) -> dict:
    logger.info("[feedback_generator] Generating feedback for topic=%s", state.topic)
    feedback = await generate_feedback(
        papers=state.papers,
        user_query=state.user_query,
        topic=state.topic
    )
    logger.info("[feedback_generator] Feedback: %s", feedback)
    return {"feedback": feedback}
