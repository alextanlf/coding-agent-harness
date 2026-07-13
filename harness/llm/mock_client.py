# harness/llm/mock_client.py
from harness.llm.base import LLMClient
from harness.core.models import Message


class MockLLMClient(LLMClient):
    """Mock LLM for unit tests. Returns scripted responses in order."""

    def __init__(self, scripted_responses: list[str]):
        self._responses = list(scripted_responses)
        self._index = 0
        self.call_count = 0
        self.call_history: list[list[Message]] = []

    async def complete(self, messages: list[Message]) -> str:
        self.call_history.append(messages)
        self.call_count += 1
        if self._index >= len(self._responses):
            raise IndexError(f"MockLLMClient: no more scripted responses (call #{self.call_count})")
        response = self._responses[self._index]
        self._index += 1
        return response
