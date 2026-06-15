"""Smoke tests — verify the package imports and basic config works."""

import sys

import pytest


def test_python_version():
    assert sys.version_info >= (3, 10), f"Python 3.10+ required, got {sys.version_info}"


def test_core_imports():
    """All exposed quorum subpackages must import cleanly on a fresh install."""
    import quorum  # noqa: F401
    import quorum.config.settings  # noqa: F401
    import quorum.scoring  # noqa: F401
    import quorum.legacy.embedding_agent.llm_client  # noqa: F401
    import quorum.legacy.embedding_agent.market_fetcher  # noqa: F401
    import quorum.legacy.embedding_agent.embedding_parser  # noqa: F401


def test_configuration_loading(monkeypatch):
    """AppConfig.load must succeed when env is set; no import-time I/O (review M7)."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    from quorum.config.settings import AppConfig

    config = AppConfig.load()
    assert config is not None
    assert config.api is not None
    assert config.market is not None
    assert config.api.openai_api_key == "test-key"


@pytest.mark.unit
def test_unit_marker():
    assert True
