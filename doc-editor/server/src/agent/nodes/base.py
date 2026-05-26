"""BaseNode — shared scaffolding for LangGraph nodes.

A Node wraps a single graph step: takes the AgentState dict, calls one or more
modules (LLM-bound tasks), and returns a partial state update. Subclasses
override `run()`; calling the instance routes through `__call__` which adds
logging + uniform error fallback.
"""
from abc import ABC, abstractmethod
from typing import Any

from core.logger import get_logger


class BaseNode(ABC):
    name: str = "BaseNode"

    def __init__(self) -> None:
        self._logger = get_logger(f"node.{self.name}")

    async def __call__(self, state: dict[str, Any]) -> dict[str, Any]:
        self._logger.debug("enter")
        try:
            out = await self.run(state)
        except Exception as e:
            self._logger.exception("node failed: %s", e)
            return self.on_error(state, e)
        self._logger.debug("exit keys=%s", list(out.keys()))
        return out

    @abstractmethod
    async def run(self, state: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError

    def on_error(self, state: dict[str, Any], err: Exception) -> dict[str, Any]:
        """Default: swallow error and return empty patch. Subclass to provide fallback."""
        return {}
