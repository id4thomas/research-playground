from langchain_core.runnables import RunnableConfig

from agent.base import BaseNode
from agent.operations.report_generation import ReportGenerationOperation

from agent.graphs.deep_research.state import DeepResearchState


class ReportNode(BaseNode):
    """집계된 결과로 최종 보고서 작성"""

    name = "report"

    async def run(self, state: DeepResearchState, config: RunnableConfig) -> dict:
        # RunnableConfig로 주입
        client = config["configurable"]["openai_client"]

        report = await ReportGenerationOperation.run(
            client=client,
            instruction=state["instruction"],
            results=state.get("results", []),
        )
        return {"report": report}


report_node = ReportNode()

__all__ = ["ReportNode", "report_node"]
