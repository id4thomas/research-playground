import operator
from typing import Annotated, Literal

from pydantic import BaseModel, Field

class PaperData(BaseModel):
    """그래프 State용 논문 모델 대이터 (HFPaper와 구분)"""
    id: str = ""
    title: str
    summary: str = ""
    authors: list[str] = []
    
    relevance_score: float = Field(default=0.0, ge=0.0, le=1.0)
    source_topic: str = ""
    source_query: str = ""

class SubGraphResult(BaseModel):
    topic: str
    papers: list[PaperData] = []


class SearchConfig(BaseModel):
    """fan-out 서브그래프에 전달되는 실행 설정. RunnableConfig.configurable로 전달."""
    max_attempts: int = 2
    search_limit: int = 5
    min_required: int = 3
    score_threshold: float = 0.5


class ResearchState(BaseModel):
    """메인 그래프 상태 관리"""
    # Input
    query: str = ""

    # Output
    topics: list[str] = []
    subgraph_results: Annotated[list[SubGraphResult], operator.add] = []
    result: list[PaperData] = []

    # Config (main graph only — subgraph config은 SearchConfig로 분리)
    num_topics: int = 3
    top_k: int = 10
    top_k_per_topic: int = 5
    

class SubGraphOutput(BaseModel):
    subgraph_results: Annotated[list[SubGraphResult], operator.add] = []


class SubGraphState(BaseModel):
    # Sub Graph Values
    search_query: str = Field("", description="Current search query")
    papers: list[PaperData] = Field(default_factory=list, description="Retrieved papers")
    feedback: str = Field("", description="Feedback from previous search iterations")
    attempt: int = Field(0, description="Current attempt iteration")
    
    # Values passed from Main Graph
    topic: str = Field("Fanned-out topic")
    user_query: str = Field("", description="Original user query")
    
    ## Config
    score_threshold: float = Field(0.5, description="Paper judge score threshold")
    max_attempts: int = Field(2, description="Maximum number of search iterations")
    search_limit: int = Field(5, description="Max items per search")
    min_required: int = Field(3, description="Minium count of papers above score threshold")