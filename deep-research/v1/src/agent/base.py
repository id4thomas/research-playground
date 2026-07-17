from abc import ABC, abstractmethod
from typing import Any

from langchain_core.messages import AIMessage
from langchain_openai import ChatOpenAI
from langgraph.graph.state import CompiledStateGraph

from config import get_settings

settings = get_settings()

class BaseAgent(ABC):
    """Base Agent"""
    _name: str = "BaseAgent"
    
    def __init__(self):
        pass
    
    @abstractmethod
    def compile_graph(self) -> CompiledStateGraph:
        raise NotImplementedError()
    
    @abstractmethod
    async def invoke(self) -> dict:
        raise NotImplementedError()