from pydantic import BaseModel, Field

class SearchOption(BaseModel):
    """검색 옵션"""
    search_limit: int = Field(10, description="검색 1회 최대 개수")
    min_required: int = Field(3, description="루프 종료를 위해 최소로 필요한 개수")
    max_iteration: int = Field(2, description="검색 루프 최대 iteration")
    score_threshold: float = Field(0.5, description="Judge threshold")
    