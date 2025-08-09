"""
Embedding Parser - Convert LLM Analysis to Sentiment Embeddings

This module takes the raw LLM market analysis and converts it into
structured sentiment embeddings that can be used for time series forecasting.
"""

import logging
import json
import re
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from datetime import datetime

from .llm_client import LLMClient, LLMResponse
from .market_fetcher import MarketContext
from ..config.settings import AppConfig


logger = logging.getLogger(__name__)


@dataclass
class SentimentEmbedding:
    """Structured sentiment embedding with metadata."""
    date: datetime
    embeddings: Dict[str, float]  # Dimension -> value mapping
    confidence_scores: Dict[str, float]  # Confidence for each dimension
    raw_analysis: str
    model_version: str
    success: bool = True
    error_message: Optional[str] = None


class EmbeddingParser:
    """
    Converts raw LLM market analysis into structured sentiment embeddings.
    
    Takes the comprehensive market context and uses LLM to extract
    quantified sentiment values for predefined dimensions.
    """
    
    def __init__(self, config: AppConfig):
        self.config = config
        self.llm_client = LLMClient(config.api)
        self.embedding_dimensions = config.market.embedding_dimensions
    
    def _create_embedding_extraction_prompt(self, market_context: MarketContext) -> str:
        """
        Create a prompt for extracting sentiment embeddings from market context.
        
        Args:
            market_context: Comprehensive market context from MarketContextFetcher
            
        Returns:
            Formatted prompt for LLM embedding extraction
        """
        
        # Create dimension descriptions for the LLM
        dimension_descriptions = {
            'tech_earnings_momentum': 'Technology sector earnings trends and momentum (positive = strong tech earnings, negative = weak tech earnings)',
            'AI_optimism': 'Market sentiment around AI/ML developments and adoption (positive = AI optimism, negative = AI skepticism)',
            'interest_rate_expectations': 'Market expectations for interest rate changes (positive = rising rates expected, negative = falling rates expected)',
            'tariff_risk': 'Concerns about trade tensions and tariff impacts (positive = low tariff risk, negative = high tariff risk)',
            'retail_investor_sentiment': 'Retail/individual investor mood and activity (positive = bullish retail sentiment, negative = bearish retail sentiment)',
            'institutional_caution': 'Large institutional investor risk appetite (positive = aggressive positioning, negative = defensive positioning)',
            'valuation_concerns': 'Market concerns about asset valuations (positive = valuations reasonable, negative = overvaluation concerns)',
            'macro_stability': 'Overall macroeconomic stability and predictability (positive = stable macro environment, negative = macro uncertainty)',
            'market_liquidity': 'Market liquidity conditions and ease of trading (positive = high liquidity, negative = liquidity concerns)',
            'crowded_trades_risk': 'Risk of overcrowded positions unwinding (positive = low crowding risk, negative = high crowding risk)'
        }
        
        prompt = f"""You are a quantitative financial analyst specializing in sentiment analysis. Based on the comprehensive market analysis provided, extract sentiment scores for specific market dimensions.

**MARKET ANALYSIS TO ANALYZE:**
{market_context.market_sentiment_raw}

**MARKET DATA CONTEXT:**
"""
        
        # Add key market data points
        for symbol, data in market_context.market_data.items():
            if 'error' not in data:
                prompt += f"- {symbol}: {data.get('change_percent', 0):+.2f}% (Volume: {data.get('volume', 0):,})\n"
        
        prompt += f"""
**NEWS SUMMARY:**
{market_context.news_summary}

**EMBEDDING DIMENSIONS TO SCORE:**

For each dimension below, provide a sentiment score from -1.0 to +1.0:
- **-1.0**: Strongly negative sentiment
- **-0.5**: Moderately negative sentiment  
- **0.0**: Neutral sentiment
- **+0.5**: Moderately positive sentiment
- **+1.0**: Strongly positive sentiment

"""
        
        for dim, desc in dimension_descriptions.items():
            prompt += f"**{dim}**: {desc}\n"
        
        prompt += """
**OUTPUT FORMAT:**
Provide your analysis in the following JSON format. Include your reasoning for each score:

```json
{
  "embeddings": {
    "tech_earnings_momentum": 0.0,
    "AI_optimism": 0.0,
    "interest_rate_expectations": 0.0,
    "tariff_risk": 0.0,
    "retail_investor_sentiment": 0.0,
    "institutional_caution": 0.0,
    "valuation_concerns": 0.0,
    "macro_stability": 0.0,
    "market_liquidity": 0.0,
    "crowded_trades_risk": 0.0
  },
  "confidence_scores": {
    "tech_earnings_momentum": 0.0,
    "AI_optimism": 0.0,
    "interest_rate_expectations": 0.0,
    "tariff_risk": 0.0,
    "retail_investor_sentiment": 0.0,
    "institutional_caution": 0.0,
    "valuation_concerns": 0.0,
    "macro_stability": 0.0,
    "market_liquidity": 0.0,
    "crowded_trades_risk": 0.0
  },
  "reasoning": {
    "tech_earnings_momentum": "Brief explanation for this score",
    "AI_optimism": "Brief explanation for this score",
    "interest_rate_expectations": "Brief explanation for this score",
    "tariff_risk": "Brief explanation for this score",
    "retail_investor_sentiment": "Brief explanation for this score",
    "institutional_caution": "Brief explanation for this score",
    "valuation_concerns": "Brief explanation for this score",
    "macro_stability": "Brief explanation for this score",
    "market_liquidity": "Brief explanation for this score",
    "crowded_trades_risk": "Brief explanation for this score"
  }
}
```

**IMPORTANT INSTRUCTIONS:**
1. Base your scores on the actual market analysis and data provided
2. Confidence scores should be 0.0-1.0 (1.0 = very confident, 0.0 = no confidence)
3. If insufficient information is available for a dimension, use 0.0 for both sentiment and confidence
4. Ensure all scores are within the specified ranges
5. Provide clear, concise reasoning for each score
6. Return ONLY the JSON object, no additional text
"""
        
        return prompt
    
    def _parse_llm_embedding_response(self, response_content: str) -> Tuple[Dict[str, float], Dict[str, float], Dict[str, str]]:
        """
        Parse LLM response to extract embeddings, confidence scores, and reasoning.
        
        Args:
            response_content: Raw LLM response content
            
        Returns:
            Tuple of (embeddings, confidence_scores, reasoning)
        """
        try:
            # Extract JSON from response (handle potential markdown formatting)
            json_match = re.search(r'```json\s*(\{.*?\})\s*```', response_content, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                # Try to find JSON without markdown formatting
                json_match = re.search(r'\{.*\}', response_content, re.DOTALL)
                if json_match:
                    json_str = json_match.group(0)
                else:
                    raise ValueError("No JSON found in response")
            
            # Parse JSON
            parsed_data = json.loads(json_str)
            
            embeddings = parsed_data.get('embeddings', {})
            confidence_scores = parsed_data.get('confidence_scores', {})
            reasoning = parsed_data.get('reasoning', {})
            
            # Validate and clean embeddings
            clean_embeddings = {}
            for dim in self.embedding_dimensions:
                if dim in embeddings:
                    value = float(embeddings[dim])
                    # Clamp to valid range
                    value = max(-1.0, min(1.0, value))
                    clean_embeddings[dim] = value
                else:
                    logger.warning(f"Missing embedding for dimension: {dim}")
                    clean_embeddings[dim] = 0.0
            
            # Validate and clean confidence scores
            clean_confidence = {}
            for dim in self.embedding_dimensions:
                if dim in confidence_scores:
                    value = float(confidence_scores[dim])
                    # Clamp to valid range
                    value = max(0.0, min(1.0, value))
                    clean_confidence[dim] = value
                else:
                    clean_confidence[dim] = 0.5  # Default moderate confidence
            
            return clean_embeddings, clean_confidence, reasoning
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing error: {e}")
            logger.error(f"Response content: {response_content}")
            raise ValueError(f"Invalid JSON in LLM response: {e}")
            
        except Exception as e:
            logger.error(f"Error parsing LLM embedding response: {e}")
            raise ValueError(f"Failed to parse embedding response: {e}")
    
    def extract_embeddings(self, market_context: MarketContext) -> SentimentEmbedding:
        """
        Extract sentiment embeddings from market context.
        
        Args:
            market_context: Comprehensive market context
            
        Returns:
            SentimentEmbedding object with quantified sentiment dimensions
        """
        if not market_context.success:
            return SentimentEmbedding(
                date=market_context.date,
                embeddings={dim: 0.0 for dim in self.embedding_dimensions},
                confidence_scores={dim: 0.0 for dim in self.embedding_dimensions},
                raw_analysis="",
                model_version=self.config.api.openai_model,
                success=False,
                error_message=f"Market context failed: {market_context.error_message}"
            )
        
        try:
            logger.info(f"Extracting sentiment embeddings for {market_context.date.strftime('%Y-%m-%d')}")
            
            # Create embedding extraction prompt
            prompt = self._create_embedding_extraction_prompt(market_context)
            
            # Get LLM response
            messages = [
                {
                    "role": "system", 
                    "content": "You are a quantitative financial analyst who converts market analysis into precise numerical sentiment scores. You always respond with valid JSON in the exact format requested."
                },
                {"role": "user", "content": prompt}
            ]
            
            llm_response = self.llm_client.generate_completion(
                messages=messages,
                temperature=0.1  # Lower temperature for more consistent numerical outputs
            )
            
            if not llm_response.success:
                return SentimentEmbedding(
                    date=market_context.date,
                    embeddings={dim: 0.0 for dim in self.embedding_dimensions},
                    confidence_scores={dim: 0.0 for dim in self.embedding_dimensions},
                    raw_analysis="",
                    model_version=self.config.api.openai_model,
                    success=False,
                    error_message=f"LLM request failed: {llm_response.error_message}"
                )
            
            # Parse the LLM response
            embeddings, confidence_scores, reasoning = self._parse_llm_embedding_response(
                llm_response.content
            )
            
            logger.info(f"Successfully extracted embeddings: {len(embeddings)} dimensions")
            logger.debug(f"Embeddings: {embeddings}")
            
            return SentimentEmbedding(
                date=market_context.date,
                embeddings=embeddings,
                confidence_scores=confidence_scores,
                raw_analysis=llm_response.content,
                model_version=self.config.api.openai_model,
                success=True
            )
            
        except Exception as e:
            logger.error(f"Error extracting embeddings: {e}")
            return SentimentEmbedding(
                date=market_context.date,
                embeddings={dim: 0.0 for dim in self.embedding_dimensions},
                confidence_scores={dim: 0.0 for dim in self.embedding_dimensions},
                raw_analysis="",
                model_version=self.config.api.openai_model,
                success=False,
                error_message=str(e)
            )
    
    def validate_embedding(self, embedding: SentimentEmbedding) -> bool:
        """
        Validate a sentiment embedding for completeness and correctness.
        
        Args:
            embedding: SentimentEmbedding to validate
            
        Returns:
            True if valid, False otherwise
        """
        try:
            # Check if embedding was successful
            if not embedding.success:
                return False
            
            # Check all required dimensions are present
            for dim in self.embedding_dimensions:
                if dim not in embedding.embeddings:
                    logger.error(f"Missing embedding dimension: {dim}")
                    return False
                
                if dim not in embedding.confidence_scores:
                    logger.error(f"Missing confidence score for dimension: {dim}")
                    return False
            
            # Check value ranges
            for dim, value in embedding.embeddings.items():
                if not isinstance(value, (int, float)):
                    logger.error(f"Invalid embedding value type for {dim}: {type(value)}")
                    return False
                
                if not -1.0 <= value <= 1.0:
                    logger.error(f"Embedding value out of range for {dim}: {value}")
                    return False
            
            for dim, confidence in embedding.confidence_scores.items():
                if not isinstance(confidence, (int, float)):
                    logger.error(f"Invalid confidence score type for {dim}: {type(confidence)}")
                    return False
                
                if not 0.0 <= confidence <= 1.0:
                    logger.error(f"Confidence score out of range for {dim}: {confidence}")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating embedding: {e}")
            return False
    
    def get_embedding_summary(self, embedding: SentimentEmbedding) -> str:
        """
        Create a human-readable summary of the embedding.
        
        Args:
            embedding: SentimentEmbedding to summarize
            
        Returns:
            Formatted summary string
        """
        if not embedding.success:
            return f"Embedding extraction failed: {embedding.error_message}"
        
        summary = f"Sentiment Embedding for {embedding.date.strftime('%Y-%m-%d')}:\n"
        summary += f"Model: {embedding.model_version}\n\n"
        
        # Sort dimensions by absolute value for most significant first
        sorted_dims = sorted(
            embedding.embeddings.items(),
            key=lambda x: abs(x[1]),
            reverse=True
        )
        
        for dim, value in sorted_dims:
            confidence = embedding.confidence_scores.get(dim, 0.0)
            sentiment = "positive" if value > 0 else "negative" if value < 0 else "neutral"
            summary += f"  {dim}: {value:+.2f} ({sentiment}, confidence: {confidence:.2f})\n"
        
        return summary 