import operator
from typing import Annotated

from langchain.agents import AgentState, create_agent
from langchain_core.messages import HumanMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import InjectedToolCallId, tool
from langgraph.config import get_stream_writer
from langgraph.prebuilt import InjectedState
from langgraph.types import Command

from agent.base import BaseNode
from agent.data.paper import PaperRetrievalData
from agent.data.search_option import SearchOption
from agent.graphs.hf_paper_search.graph import graph as search_graph
from core.llm.langchain import LangChainChatModel

from agent.graphs.deep_research_alt.state import DeepResearchAltState

SYSTEM_PROMPT = '''당신은 리서치 수퍼바이저 에이전트입니다. 유저의 관심사에 대한 논문을 라운드를 거듭하며 점진적으로 수집합니다.

paper_search 도구에 검색 토픽을 넘기면 논문 검색 서브에이전트가 실행되어 결과를 돌려줍니다.

진행 방식 (라운드 반복):
1. 한 라운드에는 지시된 개수까지만 토픽을 병렬로 paper_search 호출합니다. 처음부터 모든 것을 다 검색하려 하지 마세요
2. 라운드 결과가 돌아오면 수집된 논문들을 검토합니다: 관심사의 어떤 측면이 커버되었고 무엇이 비어 있는지 판단합니다
3. 비어 있는 측면이 있으면 다음 라운드에서 새로운 토픽으로 추가 검색합니다 (이미 탐색한 토픽과 겹치지 않게)
4. 수집된 논문이 관심사를 충분히 다루거나 지시된 최대 라운드에 도달하면 도구 호출 없이, 수집 결과에 대한 간략한 검토 의견을 작성하고 종료합니다

토픽 작성 규칙:
- 각 토픽은 간결한 자연어 구 하나로 작성합니다
- AND/OR 같은 불리언 연산자나 따옴표, 괄호는 절대 사용하지 않습니다'''

MODEL = "Qwen3.6-35B-A3B"
PARAMS = {
    "top_p": 0.8,
    "temperature": 0.7,
    # vLLM 확장 파라미터는 extra_body로 전달해야 함
    # repetition_penalty 1.5는 생성 폭주(degeneration)를 유발해 낮게 설정
    "extra_body": {"repetition_penalty": 1.05},
}


class SupervisorAgentState(AgentState):
    """create_agent 내부 state: 서브에이전트 결과를 tool의 Command update로 누적"""

    option: SearchOption
    topics: Annotated[list[str], operator.add]
    retrieved: Annotated[list[PaperRetrievalData], operator.add]


@tool
async def paper_search(
    topic: str,
    tool_call_id: Annotated[str, InjectedToolCallId],
    state: Annotated[dict, InjectedState],
    config: RunnableConfig,
) -> Command:
    """주어진 토픽에 대해 관련 논문을 검색·평가하는 검색 서브에이전트를 호출합니다.

    Args:
        topic: 논문을 검색할 토픽 (간결한 자연어 구 하나)
    """
    option = state.get("option") or SearchOption()
    # stream_mode="custom" 사용 시 토픽별 진행상황 emit (비스트리밍 실행에서는 no-op)
    writer = get_stream_writer()

    writer({"type": "search_start", "topic": topic})
    # config를 그대로 넘겨 hf_client/openai_client가 서브그래프에 주입되도록 함
    result = await search_graph.ainvoke({"topic": topic, "option": option}, config)
    final: list[PaperRetrievalData] = result.get("final", [])
    writer({
        "type": "search_done",
        "topic": topic,
        "n_papers": len(final),
        "iteration": result.get("iteration", 0),
    })

    # supervisor가 커버리지를 판단할 수 있도록 제목+요약을 결과로 전달
    papers_str = "\n".join(
        f"- {r.data.title}: {r.data.summary[:200]}" for r in final
    ) or "(수집된 논문 없음)"

    return Command(update={
        "topics": [topic],
        "retrieved": final,
        "messages": [
            ToolMessage(
                content=f"토픽 '{topic}' 검색 결과 (논문 {len(final)}편):\n{papers_str}",
                tool_call_id=tool_call_id,
            )
        ],
    })


supervisor_agent = create_agent(
    model=LangChainChatModel.get_model(MODEL, PARAMS),
    tools=[paper_search],
    system_prompt=SYSTEM_PROMPT,
    state_schema=SupervisorAgentState,
    name="supervisor_agent",
)


class SupervisorAgentNode(BaseNode):
    """create_agent 기반 수퍼바이저 실행 후 누적 결과를 outer state로 반영"""

    name = "supervisor"

    async def run(self, state: DeepResearchAltState, config: RunnableConfig) -> dict:
        human = (
            f"관심사: {state['instruction']}\n"
            f"한 라운드에 토픽 최대 {state.get('n_topics', 3)}개씩, "
            f"최대 {state.get('max_research_iteration', 2)} 라운드 안에서 탐색하세요."
        )
        result = await supervisor_agent.ainvoke(
            {
                "messages": [HumanMessage(content=human)],
                "option": state.get("option") or SearchOption(),
            },
            config,
        )
        return {
            "messages": result["messages"],
            "topics": result.get("topics", []),
            "retrieved": result.get("retrieved", []),
        }


supervisor_node = SupervisorAgentNode()

__all__ = ["SupervisorAgentNode", "supervisor_node", "supervisor_agent", "paper_search"]
