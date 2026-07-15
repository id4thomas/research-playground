from openai import AsyncOpenAI
from pydantic import BaseModel

from agent.base import BaseOperation
from agent.data.paper import PaperData


class JudgeResult(BaseModel):
    score: int

INSTRUCTION = '''검색된 논문이 주어진 토픽 및 검색 쿼리와 얼마나 관련이 있는지 평가합니다.
관련도를 0~100 사이의 정수 점수로 평가합니다. (0: 전혀 관련 없음, 100: 매우 관련 높음)
다음 JSON 형식으로 반환합니다
{"score": int}'''

# MODEL="Qwen3.6-27B"
MODEL="Qwen3.6-35B-A3B"
PARAMS={
    "top_p": 0.8,
    "temperature": 0.1,
    # vLLM 확장 파라미터는 extra_body로 전달해야 함
    # repetition_penalty 1.5는 생성 폭주(degeneration)를 유발해 낮게 설정
    "extra_body": {"repetition_penalty": 1.05}
}

class RetrievalJudgeOperation(BaseOperation):
    @classmethod
    async def run(cls, client: AsyncOpenAI, topic: str, query: str, paper: PaperData) -> float:
        messages = [
            {"role": "user", "content": INSTRUCTION},
            {
                "role": "user",
                "content": f"토픽: {topic}\n쿼리: {query}\n\n논문 제목: {paper.title}\n논문 요약: {paper.summary}"
            }
        ]

        completion = await client.chat.completions.parse(
            model=MODEL,
            messages=messages,
            response_format=JudgeResult,
            **PARAMS
        )
        result = completion.choices[0].message.parsed

        # 0~100 int -> 0~1 float로 스케일
        score = min(max(result.score, 0), 100)
        return score / 100.0
