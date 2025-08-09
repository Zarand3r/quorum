"""
Unit tests for the LLM client.
"""

import pytest
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

import openai
from openai import OpenAI

from pelosi.embedding_agent.llm_client import LLMClient, LLMResponse, RateLimiter
from pelosi.config.settings import APIConfig


class TestRateLimiter:
    """Test cases for RateLimiter."""
    
    def test_rate_limiter_creation(self):
        """Test basic RateLimiter creation."""
        limiter = RateLimiter(requests_per_minute=30)
        assert limiter.requests_per_minute == 30
        assert limiter.requests == []
    
    def test_rate_limiter_no_wait_when_under_limit(self):
        """Test that no waiting occurs when under rate limit."""
        limiter = RateLimiter(requests_per_minute=60)
        
        start_time = time.time()
        limiter.wait_if_needed()
        end_time = time.time()
        
        # Should be very fast (no waiting)
        assert end_time - start_time < 0.1
        assert len(limiter.requests) == 1
    
    @patch('time.sleep')
    def test_rate_limiter_waits_when_at_limit(self, mock_sleep):
        """Test that rate limiter waits when at limit."""
        limiter = RateLimiter(requests_per_minute=2)
        
        # Fill up the rate limit
        limiter.wait_if_needed()
        limiter.wait_if_needed()
        
        # This should trigger a wait
        limiter.wait_if_needed()
        
        mock_sleep.assert_called_once()
        # Should sleep for close to 60 seconds
        sleep_time = mock_sleep.call_args[0][0]
        assert 55 < sleep_time <= 60
    
    def test_rate_limiter_cleans_old_requests(self):
        """Test that old requests are cleaned up."""
        limiter = RateLimiter(requests_per_minute=60)
        
        # Add some old requests
        old_time = datetime.now() - timedelta(minutes=2)
        limiter.requests = [old_time, old_time]
        
        # Make a new request
        limiter.wait_if_needed()
        
        # Old requests should be cleaned up, only new one remains
        assert len(limiter.requests) == 1
        assert limiter.requests[0] > old_time


class TestLLMResponse:
    """Test cases for LLMResponse."""
    
    def test_llm_response_creation(self):
        """Test basic LLMResponse creation."""
        response = LLMResponse(
            content="Test response",
            model="gpt-4",
            tokens_used=100,
            cost_estimate=0.003,
            timestamp=datetime.now(),
            success=True
        )
        
        assert response.content == "Test response"
        assert response.model == "gpt-4"
        assert response.tokens_used == 100
        assert response.cost_estimate == 0.003
        assert response.success is True
        assert response.error_message is None
    
    def test_llm_response_with_error(self):
        """Test LLMResponse creation with error."""
        response = LLMResponse(
            content="",
            model="gpt-4",
            tokens_used=0,
            cost_estimate=0.0,
            timestamp=datetime.now(),
            success=False,
            error_message="API error occurred"
        )
        
        assert response.success is False
        assert response.error_message == "API error occurred"


class TestLLMClient:
    """Test cases for LLMClient."""
    
    @pytest.fixture
    def api_config(self):
        """API configuration for testing."""
        return APIConfig(
            openai_api_key="test-api-key",
            openai_model="gpt-4",
            openai_max_tokens=1000,
            openai_temperature=0.5,
            requests_per_minute=30
        )
    
    @pytest.fixture
    def mock_openai_response(self):
        """Mock OpenAI API response."""
        response = Mock()
        response.choices = [Mock()]
        response.choices[0].message.content = "Test LLM response content"
        response.usage.prompt_tokens = 100
        response.usage.completion_tokens = 50
        response.usage.total_tokens = 150
        return response
    
    def test_llm_client_creation(self, api_config):
        """Test basic LLMClient creation."""
        with patch('pelosi.embedding_agent.llm_client.OpenAI') as mock_openai:
            client = LLMClient(api_config)
            
            assert client.config == api_config
            mock_openai.assert_called_once_with(api_key="test-api-key")
            assert isinstance(client.rate_limiter, RateLimiter)
    
    def test_cost_estimation(self, api_config):
        """Test cost estimation for different models."""
        with patch('pelosi.embedding_agent.llm_client.OpenAI'):
            client = LLMClient(api_config)
            
            # Test GPT-4 cost
            cost = client._estimate_cost("gpt-4", 1000, 500)
            expected = (1000/1000 * 0.03) + (500/1000 * 0.06)
            assert cost == expected
            
            # Test GPT-3.5-turbo cost
            cost = client._estimate_cost("gpt-3.5-turbo", 1000, 500)
            expected = (1000/1000 * 0.001) + (500/1000 * 0.002)
            assert cost == expected
            
            # Test unknown model defaults to GPT-4
            cost = client._estimate_cost("unknown-model", 1000, 500)
            expected = (1000/1000 * 0.03) + (500/1000 * 0.06)
            assert cost == expected
    
    @patch('pelosi.embedding_agent.llm_client.OpenAI')
    def test_successful_completion(self, mock_openai_class, api_config, mock_openai_response):
        """Test successful completion generation."""
        mock_client = Mock()
        mock_openai_class.return_value = mock_client
        mock_client.chat.completions.create.return_value = mock_openai_response
        
        llm_client = LLMClient(api_config)
        
        messages = [{"role": "user", "content": "Test message"}]
        response = llm_client.generate_completion(messages)
        
        assert response.success is True
        assert response.content == "Test LLM response content"
        assert response.model == "gpt-4"
        assert response.tokens_used == 150
        assert response.cost_estimate > 0
        assert isinstance(response.timestamp, datetime)
        
        mock_client.chat.completions.create.assert_called_once_with(
            model="gpt-4",
            messages=messages,
            max_tokens=1000,
            temperature=0.5,
            timeout=30
        )
    
    @patch('pelosi.embedding_agent.llm_client.OpenAI')
    def test_rate_limit_error(self, mock_openai_class, api_config):
        """Test handling of rate limit errors."""
        mock_client = Mock()
        mock_openai_class.return_value = mock_client
        mock_client.chat.completions.create.side_effect = Exception("Rate limit exceeded")
        
        llm_client = LLMClient(api_config)
        
        messages = [{"role": "user", "content": "Test message"}]
        response = llm_client.generate_completion(messages)
        
        assert response.success is False
        assert "Unexpected error" in response.error_message
        assert response.tokens_used == 0
        assert response.cost_estimate == 0.0
    
    @patch('pelosi.embedding_agent.llm_client.OpenAI')
    def test_api_timeout_error(self, mock_openai_class, api_config):
        """Test handling of API timeout errors."""
        mock_client = Mock()
        mock_openai_class.return_value = mock_client
        mock_client.chat.completions.create.side_effect = Exception("Request timed out")
        
        llm_client = LLMClient(api_config)
        
        messages = [{"role": "user", "content": "Test message"}]
        response = llm_client.generate_completion(messages)
        
        assert response.success is False
        assert "Unexpected error" in response.error_message
        assert response.tokens_used == 0
    
    @patch('pelosi.embedding_agent.llm_client.OpenAI')
    def test_general_api_error(self, mock_openai_class, api_config):
        """Test handling of general API errors."""
        mock_client = Mock()
        mock_openai_class.return_value = mock_client
        mock_client.chat.completions.create.side_effect = Exception("General API error")
        
        llm_client = LLMClient(api_config)
        
        messages = [{"role": "user", "content": "Test message"}]
        response = llm_client.generate_completion(messages)
        
        assert response.success is False
        assert "Unexpected error" in response.error_message
    
    @patch('pelosi.embedding_agent.llm_client.OpenAI')
    def test_unexpected_error(self, mock_openai_class, api_config):
        """Test handling of unexpected errors."""
        mock_client = Mock()
        mock_openai_class.return_value = mock_client
        mock_client.chat.completions.create.side_effect = ValueError("Unexpected error")
        
        llm_client = LLMClient(api_config)
        
        messages = [{"role": "user", "content": "Test message"}]
        response = llm_client.generate_completion(messages)
        
        assert response.success is False
        assert "Unexpected error" in response.error_message
    
    @patch('pelosi.embedding_agent.llm_client.OpenAI')
    def test_custom_parameters(self, mock_openai_class, api_config, mock_openai_response):
        """Test completion with custom parameters."""
        mock_client = Mock()
        mock_openai_class.return_value = mock_client
        mock_client.chat.completions.create.return_value = mock_openai_response
        
        llm_client = LLMClient(api_config)
        
        messages = [{"role": "user", "content": "Test message"}]
        response = llm_client.generate_completion(
            messages=messages,
            model="gpt-3.5-turbo",
            max_tokens=500,
            temperature=0.8,
            timeout=60
        )
        
        assert response.success is True
        mock_client.chat.completions.create.assert_called_once_with(
            model="gpt-3.5-turbo",
            messages=messages,
            max_tokens=500,
            temperature=0.8,
            timeout=60
        )
    
    @patch('pelosi.embedding_agent.llm_client.OpenAI')
    def test_connection_test_success(self, mock_openai_class, api_config, mock_openai_response):
        """Test successful connection test."""
        mock_client = Mock()
        mock_openai_class.return_value = mock_client
        mock_client.chat.completions.create.return_value = mock_openai_response
        
        llm_client = LLMClient(api_config)
        
        result = llm_client.test_connection()
        
        assert result is True
        mock_client.chat.completions.create.assert_called_once()
    
    @patch('pelosi.embedding_agent.llm_client.OpenAI')
    def test_connection_test_failure(self, mock_openai_class, api_config):
        """Test failed connection test."""
        mock_client = Mock()
        mock_openai_class.return_value = mock_client
        mock_client.chat.completions.create.side_effect = Exception("Connection failed")
        
        llm_client = LLMClient(api_config)
        
        result = llm_client.test_connection()
        
        assert result is False
    
    @patch('time.sleep')
    @patch('pelosi.embedding_agent.llm_client.OpenAI')
    def test_rate_limiting_integration(self, mock_openai_class, mock_sleep, api_config, mock_openai_response):
        """Test that rate limiting is applied during requests."""
        mock_client = Mock()
        mock_openai_class.return_value = mock_client
        mock_client.chat.completions.create.return_value = mock_openai_response
        
        # Create client with very low rate limit
        api_config.requests_per_minute = 1
        llm_client = LLMClient(api_config)
        
        messages = [{"role": "user", "content": "Test message"}]
        
        # First request should succeed without delay
        response1 = llm_client.generate_completion(messages)
        assert response1.success is True
        
        # Second request should trigger rate limiting
        response2 = llm_client.generate_completion(messages)
        assert response2.success is True
        
        # Should have called sleep for rate limiting
        mock_sleep.assert_called_once() 