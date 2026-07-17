from openai import AsyncOpenAI

from agent.base import BaseOperation
from agent.data.result import TopicRetrievalResult


INSTRUCTION = '''유저의 관심사에 대해 수집된 논문들을 바탕으로 최종 리서치 보고서를 마크다운으로 작성합니다.
- 관심사에 대한 전체 요약으로 시작합니다
- 토픽별 섹션을 만들어 주요 논문들과 핵심 내용을 정리합니다
- 논문을 언급할 때는 제목을 명시합니다
- 마지막에 종합 결론을 작성합니다'''

# MODEL="Qwen3.6-27B"
MODEL="Qwen3.6-35B-A3B"
PARAMS={
    "top_p": 0.8,
    "temperature": 0.7,
    # 보고서가 끝맺지 못하고 컨텍스트 한계까지 생성되는 것 방지
    "max_tokens": 4096,
    # vLLM 확장 파라미터는 extra_body로 전달해야 함
    # 장문 생성에서 repetition_penalty 1.5는 EOS까지 억눌러 무한 생성을 유발하므로 낮게 설정
    "extra_body": {"repetition_penalty": 1.05}
}


def _format_results(results: list[TopicRetrievalResult]) -> str:
    lines = []
    for r in results:
        lines.append(f"## 토픽: {r.topic}")
        if not r.result:
            lines.append("(수집된 논문 없음)")
        for p in r.result:
            lines.append(f"- {p.data.title} (score: {p.score:.2f})\n  {p.data.summary[:500]}")
        lines.append("")
    return "\n".join(lines)


class ReportGenerationOperation(BaseOperation):
    @classmethod
    async def run(
        cls, client: AsyncOpenAI, instruction: str, results: list[TopicRetrievalResult]
    ) -> str:
        messages = [
            {"role": "user", "content": INSTRUCTION},
            {
                "role": "user",
                "content": f"관심사: {instruction}\n\n수집된 논문:\n{_format_results(results)}"
            }
        ]

        completion = await client.chat.completions.create(
            model=MODEL,
            messages=messages,
            **PARAMS
        )
        return completion.choices[0].message.content
