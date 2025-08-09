"""
LLM client for OpenAI API integration.

Handles communication with OpenAI API for market context analysis
and sentiment embedding generation.
"""

import time
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime, timedelta

import openai
from openai import OpenAI

from ..config.settings import APIConfig


logger = logging.getLogger(__name__)


@dataclass
class LLMResponse:
    """Structured response from LLM."""
    content: str
    model: str
    tokens_used: int
    cost_estimate: float
    timestamp: datetime
    success: bool = True
    error_message: Optional[str] = None


class RateLimiter:
    """Simple rate limiter for API calls."""
    
    def __init__(self, requests_per_minute: int = 60):
        self.requests_per_minute = requests_per_minute
        self.requests = []
    
    def wait_if_needed(self):
        """Wait if we're approaching rate limits."""
        now = datetime.now()
        # Remove requests older than 1 minute
        self.requests = [req_time for req_time in self.requests 
                        if now - req_time < timedelta(minutes=1)]
        
        if len(self.requests) >= self.requests_per_minute:
            # Wait until the oldest request is over 1 minute old
            sleep_time = 60 - (now - self.requests[0]).total_seconds()
            if sleep_time > 0:
                logger.info(f"Rate limiting: sleeping for {sleep_time:.1f} seconds")
                time.sleep(sleep_time)
        
        self.requests.append(now)


class LLMClient:
    """Client for interacting with OpenAI's LLM API."""
    
    def __init__(self, config: APIConfig):
        self.config = config
        self.client = OpenAI(api_key=config.openai_api_key)
        self.rate_limiter = RateLimiter(config.requests_per_minute)
        
        # Token cost estimates (per 1K tokens)
        self.token_costs = {
            'gpt-4': {'input': 0.03, 'output': 0.06},
            'gpt-4-turbo': {'input': 0.01, 'output': 0.03},
            'gpt-3.5-turbo': {'input': 0.001, 'output': 0.002},
        }
    
    def _estimate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        """Estimate the cost of an API call."""
        if model not in self.token_costs:
            model = 'gpt-4'  # Default to most expensive for safety
        
        costs = self.token_costs[model]
        input_cost = (input_tokens / 1000) * costs['input']
        output_cost = (output_tokens / 1000) * costs['output']
        return input_cost + output_cost
    
    def generate_completion(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        timeout: int = 30
    ) -> LLMResponse:
        """
        Generate a completion using the OpenAI API.
        
        Args:
            messages: List of message dictionaries with 'role' and 'content'
            model: Model to use (defaults to config model)
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature
            timeout: Request timeout in seconds
            
        Returns:
            LLMResponse object with the completion and metadata
        """
        # Use config defaults if not specified
        model = model or self.config.openai_model
        max_tokens = max_tokens or self.config.openai_max_tokens
        temperature = temperature or self.config.openai_temperature
        
        # Rate limiting
        self.rate_limiter.wait_if_needed()
        
        try:
            logger.info(f"Making LLM request to {model}")
            start_time = time.time()
            
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                timeout=timeout
            )
            
            elapsed_time = time.time() - start_time
            
            # Extract response data
            content = response.choices[0].message.content
            input_tokens = response.usage.prompt_tokens
            output_tokens = response.usage.completion_tokens
            total_tokens = response.usage.total_tokens
            
            cost_estimate = self._estimate_cost(model, input_tokens, output_tokens)
            
            logger.info(
                f"LLM request completed in {elapsed_time:.2f}s. "
                f"Tokens: {total_tokens}, Cost: ${cost_estimate:.4f}"
            )
            
            return LLMResponse(
                content=content,
                model=model,
                tokens_used=total_tokens,
                cost_estimate=cost_estimate,
                timestamp=datetime.now(),
                success=True
            )
            
        except openai.RateLimitError as e:
            logger.error(f"Rate limit exceeded: {e}")
            return LLMResponse(
                content="",
                model=model,
                tokens_used=0,
                cost_estimate=0.0,
                timestamp=datetime.now(),
                success=False,
                error_message=f"Rate limit exceeded: {e}"
            )
            
        except openai.APITimeoutError as e:
            logger.error(f"API timeout: {e}")
            return LLMResponse(
                content="",
                model=model,
                tokens_used=0,
                cost_estimate=0.0,
                timestamp=datetime.now(),
                success=False,
                error_message=f"API timeout: {e}"
            )
            
        except openai.APIError as e:
            logger.error(f"OpenAI API error: {e}")
            return LLMResponse(
                content="",
                model=model,
                tokens_used=0,
                cost_estimate=0.0,
                timestamp=datetime.now(),
                success=False,
                error_message=f"API error: {e}"
            )
            
        except Exception as e:
            logger.error(f"Unexpected error in LLM request: {e}")
            return LLMResponse(
                content="",
                model=model,
                tokens_used=0,
                cost_estimate=0.0,
                timestamp=datetime.now(),
                success=False,
                error_message=f"Unexpected error: {e}"
            )
    
    def test_connection(self) -> bool:
        """Test the OpenAI API connection."""
        try:
            test_messages = [
                {"role": "user", "content": "Hello, this is a test message."}
            ]
            response = self.generate_completion(
                messages=test_messages,
                max_tokens=10
            )
            return response.success
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False 