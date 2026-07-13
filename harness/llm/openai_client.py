# harness/llm/openai_client.py
import asyncio
import logging
from harness.llm.base import LLMClient
from harness.core.models import Message

logger = logging.getLogger(__name__)


class OpenAIClient(LLMClient):
    def __init__(self, api_key: str, model: str = "gpt-4o"):
        from openai import OpenAI, AsyncOpenAI
        self._api_key = api_key
        self._model = model
        self._client = AsyncOpenAI(api_key=api_key)

    async def complete(self, messages: list[Message]) -> str:
        import openai
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = await self._client.chat.completions.create(
                    model=self._model,
                    messages=[{"role": m.role, "content": m.content} for m in messages],
                )
                return response.choices[0].message.content
            except openai.RateLimitError:
                if attempt < max_retries - 1:
                    wait = 2 ** attempt
                    logger.warning(f"Rate limited, retrying in {wait}s (attempt {attempt + 1}/{max_retries})")
                    await asyncio.sleep(wait)
                else:
                    raise
            except openai.APIError as e:
                raise LLMError(f"OpenAI API error: {e}") from e


class LLMError(Exception):
    pass
