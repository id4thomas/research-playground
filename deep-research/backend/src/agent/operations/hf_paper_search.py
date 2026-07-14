from agent.base import BaseOperation
from agent.data.paper import PaperData

from client.huggingface import (
    HuggingfacePapersClient,
    Paper as HFPaper
)


class HFPaperSearchOperation(BaseOperation):
    @classmethod
    async def run(cls, client: HuggingfacePapersClient, query: str, limit: int = 5) -> list[PaperData]:
        hf_papers: list[HFPaper] = await client.search(query, limit=limit)
        
        datas = []
        for paper in hf_papers:
            data = PaperData(
                id=paper.id,
                title=paper.title,
                summary=paper.summary,
                authors=[a.name for a in paper.authors],
            )
            datas.append(data)
        return datas
