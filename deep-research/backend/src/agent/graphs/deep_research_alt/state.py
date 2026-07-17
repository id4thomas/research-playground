import operator
from typing import Annotated, TypedDict

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages

from agent.data.paper import PaperRetrievalData
from agent.data.result import TopicRetrievalResult
from agent.data.search_option import SearchOption


class DeepResearchAltState(TypedDict, total=False):
    # Input
    instruction: str  # 유저 관심사
    n_topics: int  # supervisor에게 권장하는 초기 토픽 개수
    option: SearchOption  # 서브에이전트(hf_paper_search) 검색 옵션
    max_research_iteration: int  # supervisor의 tool calling 라운드 최대 횟수

    # Intermediate
    messages: Annotated[list[AnyMessage], add_messages]  # supervisor 대화 히스토리
    topics: Annotated[list[str], operator.add]  # tool call로 탐색된 토픽 누적
    retrieved: Annotated[list[PaperRetrievalData], operator.add]  # 서브에이전트 final 누적
    research_iteration: int  # 완료된 tool calling 라운드 횟수

    # Output
    results: list[TopicRetrievalResult]  # 토픽별 집계 결과
    report: str  # 최종 보고서 (마크다운)
