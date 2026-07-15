import operator
from typing import Annotated, TypedDict

from agent.data.paper import PaperRetrievalData
from agent.data.result import TopicRetrievalResult
from agent.data.search_option import SearchOption


class DeepResearchState(TypedDict, total=False):
    # Input
    instruction: str  # 유저 관심사
    n_topics: int  # 라운드당 생성할 검색 토픽 개수
    option: SearchOption  # 서브에이전트(hf_paper_search) 검색 옵션
    max_research_iteration: int  # 탐색 라운드(탐색→검토→추가탐색) 최대 횟수

    # Intermediate
    pending_topics: list[str]  # 이번 라운드에 탐색할 토픽
    topics: Annotated[list[str], operator.add]  # 탐색 완료된 토픽 누적
    retrieved: Annotated[list[PaperRetrievalData], operator.add]  # 서브에이전트 final 누적
    research_iteration: int  # 완료된 탐색 라운드 횟수
    review: str  # 마지막 검토 의견

    # Output
    results: list[TopicRetrievalResult]  # 토픽별 집계 결과
    report: str  # 최종 보고서 (마크다운)
