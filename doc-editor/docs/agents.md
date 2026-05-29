# Agent, LangGraph 설계
## Base 구조
### 계층
Agent (Graph) > Node > Operation
- Agent: LangGraph graph를 감싸는 최상위 단위
- Node: 필요한 Operation / SubGraph를 감싸서 langgraph node 명세에 맞춰줌
    - node는 각 그래프에 맞게 구현하는 것이 목표, 그래프 a가 그래프 b의 노드를 임포트 하는 것은 지양
- Operation: 실제 동작 단위, langgraph와 무관하게 사용가능하도록 동작 로직을 관리
    - node 대신 operation을 여러 군데에 임포트 해서 사용

### Base 인터페이스
#### BaseAgent
- langgraph graph의 invoke를 거의 그대로 (state in state out) 활용

인터페이스
```python3
class BaseAgent(ABC):
    """Base agent interface."""
    _name: str = "BaseAgent"

    @abstractmethod
    def compile_graph(self) -> CompiledStateGraph:
        raise NotImplementedError()

    @abstractmethod
    async def invoke(self, state: dict) -> dict:
        raise NotImplementedError()
```
    

#### BaseNode
- MyNode()를 그대로 add_node로 그래프 등록 가능하게 call 인터페이스를 langgraph 노드 인터페이스랑 맞춤 (state, config)
- 상속받은 노드들은 run을 구현해서 실행

인터페이스
```python3
from langgraph.types import Command

StateT = TypeVar("StateT", bound=dict[str, Any])
NodeReturn = dict[str, Any] | Command

class BaseNode(ABC, Generic[StateT]):
    async def __call__(
        self,
        state: StateT,
        config: RunnableConfig | None = None,
    ) -> NodeReturn:
        ...
    
    @abstractmethod
    async def run(self, state: StateT, config: RunnableConfig) -> NodeReturn:
        raise NotImplementedError
```


#### BaseOperation
- langgraph와 무관하게 단독으로 실행하는 함수
    
인터페이스
```python3
class BaseOperation(ABC):
    @classmethod
    @abstractmethod
    async def run(cls, *args, **kwargs):
        raise NotImplementedError
```
    

## SubGraph 호출

상위 Graph, SubGraph간의 state 의존성 최소화 하기 위해서 래핑 처리

- Subgraph를 그대로 add_node로 추가하지 말고 함수로 래핑해서 node등록
- 참고 자료: “[Call a subgraph inside a node](https://docs.langchain.com/oss/python/langgraph/use-subgraphs#call-a-subgraph-inside-a-node)”
    - When the parent graph and subgraph have different state schemas (no shared keys), invoke the subgraph inside a node function

예시
```python3
class MyAgent(BaseAgent):
    def compile_graph(self) -> CompiledStateGraph:
        subgraph = build_subgraph()
        
        async def _subagent(state: AgentState) -> dict:
            result = await subgraph.ainvoke(
                {subgraph_state}
            )
            return {postprocess to upper graph state spec}
        
        b = StateGraph(AgentState)
        b.add_node("_subagent", _subagent)
        ...
```