# harness/llm/base.py
from abc import ABC, abstractmethod
from harness.core.models import Message


class LLMClient(ABC):
    @abstractmethod
    async def complete(self, messages: list[Message]) -> str:
        """Call the LLM with messages, return raw text response."""
        ...
