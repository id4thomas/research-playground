from enum import StrEnum
import json

from pydantic import BaseModel, Field, create_model

from agent.research.states import PaperData, SubGraphState
from core.llm.langchain import LangChainChatModel
from core.logger import get_logger

logger = get_logger(__name__)

MODEL_NAME = "Qwen3.5-35B-A3B"


INSTRUCTION_TEMPLATE = """각 논문의 탐색 방향과의 관련도를 0.0~1.0으로 채점하세요.

유저 쿼리: {user_query}
검색 방향: {topic}

논문 목록:
{paper_info}

다음 JSON 형식으로 반환합니다
{{
    "scores": [
        {{
            "paper_id": 논문ID,
            "score": float # 0.0~1.0 사이의 점수
        }}
    ]
}}
"""

def build_judge_response_schema(paper_ids: list[str]) -> type[BaseModel]:
    """
    StrEnum으로 동적 출력 스키마 구성 -> PaperId 생성 제어
    """
    PaperIdEnum = StrEnum("PaperIdEnum", {pid: pid for pid in paper_ids})

    class PaperScore(BaseModel):
        paper_id: PaperIdEnum
        score: float = Field(ge=0.0, le=1.0)

    ScoringResponse = create_model(
        "ScoringResponse",
        scores=(list[PaperScore], ...),
    )

    return ScoringResponse

async def judge_papers(
    papers: list[PaperData],
    user_query: str,
    topic: str,
    max_summary_len: int = 256
) -> dict:
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
    
    # Build Output Schema
    paper_ids = [p.id for p in papers]
    ScoringResponse = build_judge_response_schema(paper_ids)
    
    # Generate
    messages = [
        {"role": "user", "content": instruction}
    ]
    response = await LangChainChatModel.chat(messages, model_name=MODEL_NAME, response_format=ScoringResponse)
    data = json.loads(response.content)
    score_map = {s["paper_id"]: s["score"] for s in data["scores"]}
    return score_map

async def judge_node(state: SubGraphState) -> dict:
    """미채점 논문에 대해 topic 관련도 스코어만 매긴다."""
    logger.info("[judge] Judging papers for topic=%s, %d total", state.topic, len(state.papers))

    scored = [p for p in state.papers if p.relevance_score > 0]
    unscored = [p for p in state.papers if p.relevance_score == 0 and p.id]

    if unscored:
        logger.info("[judge] Scoring %d unscored papers", len(unscored))
        score_map = await judge_papers(
            papers=unscored,
            user_query=state.user_query,
            topic=state.topic
        )
        for p in unscored:
            if p.id in score_map:
                p.relevance_score = float(score_map[p.id])

    # threshold 필터링
    all_papers = scored + unscored
    filtered = [p for p in all_papers if p.relevance_score >= state.score_threshold]
    logger.info("[judge] %d papers passed threshold (%.2f)", len(filtered), state.score_threshold)
    return {"papers": filtered}
