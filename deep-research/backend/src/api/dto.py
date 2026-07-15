from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    topic: str
    search_limit: int = Field(10, description="검색 1회 최대 개수")
    min_required: int = Field(3, description="루프 종료를 위해 최소로 필요한 개수")
    max_iteration: int = Field(2, description="검색 루프 최대 iteration")
    score_threshold: float = Field(0.5, description="Judge threshold")


class PaperResult(BaseModel):
    id: str
    title: str
    summary: str
    authors: list[str]
    score: float
    source_query: str


class SearchResponse(BaseModel):
    topic: str
    iteration: int
    papers: list[PaperResult]


class DeepResearchRequest(BaseModel):
    instruction: str = Field(description="유저 관심사")
    n_topics: int = Field(3, description="라운드당 생성할 검색 토픽 개수")
    max_research_iteration: int = Field(2, description="탐색 라운드(탐색→검토→추가탐색) 최대 횟수")
    search_limit: int = Field(10, description="검색 1회 최대 개수")
    min_required: int = Field(3, description="루프 종료를 위해 최소로 필요한 개수")
    max_iteration: int = Field(2, description="검색 루프 최대 iteration")
    score_threshold: float = Field(0.5, description="Judge threshold")


class TopicPapersResult(BaseModel):
    topic: str
    papers: list[PaperResult]


class DeepResearchResponse(BaseModel):
    instruction: str
    topics: list[str]
    review: str
    results: list[TopicPapersResult]
    report: str
