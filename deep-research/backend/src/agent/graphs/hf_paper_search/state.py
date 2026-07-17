from typing import TypedDict

from agent.data.paper import PaperData, PaperRetrievalData
from agent.data.search_option import SearchOption


class SearchState(TypedDict, total=False):
    # Input
    topic: str
    option: SearchOption    
    
    # Intermediate
    query: str
    retrieved: list[PaperData] # Retrieve되고 Judge 전
    iteration: int # 완료된 검색 루프 횟수
    
    # Output
    final: list[PaperRetrievalData] # 최종 결과물