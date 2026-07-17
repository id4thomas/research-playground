from pydantic import BaseModel, Field

class PaperData(BaseModel):
    """논문 정보"""
    id: str = ""
    title: str
    summary: str = ""
    authors: list[str] = []

class PaperRetrievalData(BaseModel):
    data: PaperData
    
    score: float = 0.0
    source_query: str = ""
    source_topic: str = ""