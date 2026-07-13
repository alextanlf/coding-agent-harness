# tests/test_openai_client.py
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from harness.llm.openai_client import OpenAIClient
from harness.core.models import Message

@pytest.mark.asyncio
async def test_openai_client_calls_api():
    client = OpenAIClient(api_key="sk-test", model="gpt-4o")
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = '{"type": "task_complete"}'

    with patch.object(client, '_client') as mock_client:
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        result = await client.complete([Message("user", "hello")])
        assert result == '{"type": "task_complete"}'
        mock_client.chat.completions.create.assert_called_once()

@pytest.mark.asyncio
async def test_openai_client_passes_model():
    client = OpenAIClient(api_key="sk-test", model="gpt-4o-mini")
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "ok"

    with patch.object(client, '_client') as mock_client:
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
        await client.complete([Message("user", "hi")])
        call_kwargs = mock_client.chat.completions.create.call_args.kwargs
        assert call_kwargs["model"] == "gpt-4o-mini"

@pytest.mark.asyncio
async def test_openai_client_retries_on_rate_limit():
    client = OpenAIClient(api_key="sk-test", model="gpt-4o")
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "ok"

    import openai
    rate_limit_error = openai.RateLimitError(
        message="rate limited", response=MagicMock(), body=None
    )

    with patch.object(client, '_client') as mock_client:
        mock_client.chat.completions.create = AsyncMock(
            side_effect=[rate_limit_error, mock_response]
        )
        result = await client.complete([Message("user", "hi")])
        assert result == "ok"
        assert mock_client.chat.completions.create.call_count == 2
