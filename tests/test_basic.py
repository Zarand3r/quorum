"""
Basic tests to verify the core system is working.
"""

import pytest
import sys
import os
from pathlib import Path

# Add the project root to Python path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def test_python_version():
    """Test that we're running on Python 3.10+."""
    assert sys.version_info >= (3, 10), f"Python 3.10+ required, got {sys.version_info}"


def test_core_imports():
    """Test that core modules can be imported."""
    try:
        from pelosi.config.settings import AppConfig
        from pelosi.embedding_agent.llm_client import LLMClient
        from pelosi.embedding_agent.market_fetcher import MarketContextFetcher
        from pelosi.embedding_agent.embedding_parser import EmbeddingParser
    except ImportError as e:
        pytest.fail(f"Core import failed: {e}")


def test_configuration_loading():
    """Test that configuration can be loaded."""
    from pelosi.config.settings import AppConfig
    
    config = AppConfig.load()
    assert config is not None
    assert hasattr(config, 'api')
    assert hasattr(config, 'market')


@pytest.mark.unit
def test_unit_marker():
    """Test that unit test marker works."""
    assert True


@pytest.mark.integration
def test_integration_marker():
    """Test that integration test marker works."""
    assert True 