"""Tests for configuration module."""

import os
from unittest.mock import patch

import pytest

from meta_agent_mcp.config import Settings


def test_settings_defaults():
    """Test that settings have correct default values."""
    with patch.dict(os.environ, {}, clear=True):
        settings = Settings()
        
        assert settings.meta_agent_model == "x-ai/grok-4-fast"
        assert settings.meta_agent_host == "localhost"
        assert settings.meta_agent_port == 8000
        assert settings.log_level == "INFO"
        assert settings.default_beam_width == 3
        assert settings.default_mcts_simulations == 50


def test_settings_from_env():
    """Test that settings are loaded from environment variables."""
    env_vars = {
        "OPENROUTER_API_KEY": "test-api-key",
        "META_AGENT_MODEL": "anthropic/claude-3.5-sonnet",
        "META_AGENT_PORT": "9000",
        "LOG_LEVEL": "DEBUG",
    }
    
    with patch.dict(os.environ, env_vars, clear=True):
        settings = Settings()
        
        assert settings.openrouter_api_key == "test-api-key"
        assert settings.meta_agent_model == "anthropic/claude-3.5-sonnet"
        assert settings.meta_agent_port == 9000
        assert settings.log_level == "DEBUG"


def test_beam_width_validation():
    """Test beam width validation bounds."""
    with patch.dict(os.environ, {"DEFAULT_BEAM_WIDTH": "5"}, clear=True):
        settings = Settings()
        assert settings.default_beam_width == 5
    
    # Test out of bounds
    with pytest.raises(ValueError):
        with patch.dict(os.environ, {"DEFAULT_BEAM_WIDTH": "15"}, clear=True):
            Settings()


def test_mcts_simulations_validation():
    """Test MCTS simulations validation bounds."""
    with patch.dict(os.environ, {"DEFAULT_MCTS_SIMULATIONS": "100"}, clear=True):
        settings = Settings()
        assert settings.default_mcts_simulations == 100

