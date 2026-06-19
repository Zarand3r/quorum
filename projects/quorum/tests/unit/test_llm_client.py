"""Unit tests for ``quorum.legacy.embedding_agent.llm_client``."""

import time
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch

import openai
import pytest

from quorum.config.settings import APIConfig
from quorum.legacy.embedding_agent.llm_client import (
    LLMClient,
    LLMResponse,
    RateLimiter,
)


class TestRateLimiter:
    def test_rate_limiter_creation(self):
        limiter = RateLimiter(requests_per_minute=30)
        assert limiter.requests_per_minute == 30
        assert len(limiter.requests) == 0

    def test_rate_limiter_no_wait_when_under_limit(self):
        limiter = RateLimiter(requests_per_minute=60)
        start = time.monotonic()
        limiter.wait_if_needed()
        elapsed = time.monotonic() - start
        assert elapsed < 0.1
        assert len(limiter.requests) == 1

    @patch('time.sleep')
    def test_rate_limiter_waits_when_at_limit(self, mock_sleep):
        limiter = RateLimiter(requests_per_minute=2)
        limiter.wait_if_needed()
        limiter.wait_if_needed()
        limiter.wait_if_needed()

        mock_sleep.assert_called_once()
        sleep_time = mock_sleep.call_args[0][0]
        assert 55 < sleep_time <= 60

    def test_rate_limiter_cleans_old_requests(self):
        limiter = RateLimiter(requests_per_minute=60)
        old_time = datetime.now(timezone.utc) - timedelta(minutes=2)
        limiter.requests.extend([old_time, old_time])

        limiter.wait_if_needed()

        assert len(limiter.requests) == 1
        assert limiter.requests[0] > old_time


class TestLLMResponse:
    def test_llm_response_creation(self):
        response = LLMResponse(
            content="Test response",
            model="gpt-4",
            tokens_used=100,
            cost_estimate=0.003,
            timestamp=datetime.now(timezone.utc),
            success=True,
        )
        assert response.content == "Test response"
        assert response.tokens_used == 100
        assert response.success is True
        assert response.error_message is None

    def test_llm_response_with_error(self):
        response = LLMResponse(
            content="",
            model="gpt-4",
            tokens_used=0,
            cost_estimate=0.0,
            timestamp=datetime.now(timezone.utc),
            success=False,
            error_message="API error occurred",
        )
        assert response.success is False
        assert response.error_message == "API error occurred"


class TestLLMClient:
    @pytest.fixture
    def api_config(self) -> APIConfig:
        return APIConfig(
            openai_api_key="test-api-key",
            openai_model="gpt-4",
            openai_max_tokens=1000,
            openai_temperature=0.5,
            requests_per_minute=30,
        )

    @pytest.fixture
    def mock_openai_response(self) -> Mock:
        response = Mock()
        response.choices = [Mock()]
        response.choices[0].message.content = "Test LLM response content"
        response.usage.prompt_tokens = 100
        response.usage.completion_tokens = 50
        response.usage.total_tokens = 150
        return response

    def test_llm_client_creation(self, api_config):
        with patch('quorum.legacy.embedding_agent.llm_client.OpenAI') as mock_openai:
            client = LLMClient(api_config)
            assert client.config == api_config
            mock_openai.assert_called_once_with(api_key="test-api-key")
            assert isinstance(client.rate_limiter, RateLimiter)

    def test_cost_estimation(self, api_config):
        with patch('quorum.legacy.embedding_agent.llm_client.OpenAI'):
            client = LLMClient(api_config)

            assert client._estimate_cost("gpt-4", 1000, 500) == pytest.approx(
                (1000 / 1000 * 0.03) + (500 / 1000 * 0.06)
            )
            assert client._estimate_cost("gpt-3.5-turbo", 1000, 500) == pytest.approx(
                (1000 / 1000 * 0.001) + (500 / 1000 * 0.002)
            )
            # Unknown model falls back to gpt-4 pricing (the safe-on-the-high-side default).
            assert client._estimate_cost("unknown-model", 1000, 500) == pytest.approx(
                (1000 / 1000 * 0.03) + (500 / 1000 * 0.06)
            )

    @patch('quorum.legacy.embedding_agent.llm_client.OpenAI')
    def test_successful_completion(self, mock_openai_class, api_config, mock_openai_response):
        mock_client = Mock()
        mock_openai_class.return_value = mock_client
        mock_client.chat.completions.create.return_value = mock_openai_response

        llm_client = LLMClient(api_config)
        messages = [{"role": "user", "content": "Test message"}]
        response = llm_client.generate_completion(messages)

        assert response.success is True
        assert response.content == "Test LLM response content"
        assert response.tokens_used == 150
        assert response.cost_estimate > 0
        assert response.timestamp.tzinfo is timezone.utc

        mock_client.chat.completions.create.assert_called_once_with(
            model="gpt-4",
            messages=messages,
            max_tokens=1000,
            temperature=0.5,
            timeout=30,
        )

    @patch('quorum.legacy.embedding_agent.llm_client.OpenAI')
    def test_openai_error_returns_failure_response(self, mock_openai_class, api_config):
        """All OpenAI library errors collapse into LLMResponse(success=False).

        After the m1/m2 cleanup, ``llm_client`` no longer has 4 near-identical
        ``except`` blocks — it has a single ``(RateLimitError, APITimeoutError,
        APIError)`` block.
        """
        mock_client = Mock()
        mock_openai_class.return_value = mock_client

        # Construct a real openai.APIError so the typed-handler matches.
        api_error = openai.APIError(message="boom", request=Mock(), body=None)
        mock_client.chat.completions.create.side_effect = api_error

        llm_client = LLMClient(api_config)
        response = llm_client.generate_completion([{"role": "user", "content": "x"}])

        assert response.success is False
        assert response.tokens_used == 0
        assert response.cost_estimate == 0.0
        assert "APIError" in (response.error_message or "")

    @patch('quorum.legacy.embedding_agent.llm_client.OpenAI')
    def test_non_openai_exception_propagates(self, mock_openai_class, api_config):
        """A ValueError from elsewhere is *not* swallowed (review m1) — it
        propagates so a programmer bug doesn't masquerade as an API failure."""
        mock_client = Mock()
        mock_openai_class.return_value = mock_client
        mock_client.chat.completions.create.side_effect = ValueError("bug")

        llm_client = LLMClient(api_config)
        with pytest.raises(ValueError, match="bug"):
            llm_client.generate_completion([{"role": "user", "content": "x"}])

    @patch('quorum.legacy.embedding_agent.llm_client.OpenAI')
    def test_custom_parameters(self, mock_openai_class, api_config, mock_openai_response):
        mock_client = Mock()
        mock_openai_class.return_value = mock_client
        mock_client.chat.completions.create.return_value = mock_openai_response

        llm_client = LLMClient(api_config)
        response = llm_client.generate_completion(
            messages=[{"role": "user", "content": "x"}],
            model="gpt-3.5-turbo",
            max_tokens=500,
            temperature=0.8,
            timeout=60,
        )

        assert response.success is True
        mock_client.chat.completions.create.assert_called_once_with(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": "x"}],
            max_tokens=500,
            temperature=0.8,
            timeout=60,
        )

    @patch('quorum.legacy.embedding_agent.llm_client.OpenAI')
    def test_connection_test_success(self, mock_openai_class, api_config, mock_openai_response):
        mock_client = Mock()
        mock_openai_class.return_value = mock_client
        mock_client.chat.completions.create.return_value = mock_openai_response

        llm_client = LLMClient(api_config)
        assert llm_client.test_connection() is True

    @patch('quorum.legacy.embedding_agent.llm_client.OpenAI')
    def test_connection_test_failure(self, mock_openai_class, api_config):
        mock_client = Mock()
        mock_openai_class.return_value = mock_client
        mock_client.chat.completions.create.side_effect = Exception("Connection failed")

        llm_client = LLMClient(api_config)
        assert llm_client.test_connection() is False

    @patch('time.sleep')
    @patch('quorum.legacy.embedding_agent.llm_client.OpenAI')
    def test_rate_limiting_integration(
        self,
        mock_openai_class,
        mock_sleep,
        api_config,
        mock_openai_response,
    ):
        mock_client = Mock()
        mock_openai_class.return_value = mock_client
        mock_client.chat.completions.create.return_value = mock_openai_response

        api_config.requests_per_minute = 1
        llm_client = LLMClient(api_config)
        messages = [{"role": "user", "content": "x"}]

        assert llm_client.generate_completion(messages).success is True
        assert llm_client.generate_completion(messages).success is True

        mock_sleep.assert_called_once()
