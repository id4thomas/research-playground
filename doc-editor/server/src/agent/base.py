from abc import ABC, abstractmethod

from langgraph.graph.state import CompiledStateGraph


class BaseAgent(ABC):
    """Base agent interface."""
    _name: str = "BaseAgent"

    @abstractmethod
    def compile_graph(self) -> CompiledStateGraph:
        raise NotImplementedError()

    @abstractmethod
    async def invoke(self, state: dict) -> dict:
        raise NotImplementedError()
