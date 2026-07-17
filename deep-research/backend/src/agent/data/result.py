from pydantic import BaseModel

from agent.data.paper import PaperRetrievalData

class TopicRetrievalResult(BaseModel):
    topic: str
    result: list[PaperRetrievalData]