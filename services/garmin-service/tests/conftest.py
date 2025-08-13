"""
Test configuration and fixtures for Garmin service tests
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
import os

# Set test environment variables
os.environ["ENVIRONMENT"] = "test"
os.environ["SECRET_KEY"] = "test_secret_key_for_testing_only"
os.environ["DATABASE_URL"] = "postgresql+asyncpg://test:test@localhost:5433/test_db"
os.environ["REDIS_URL"] = "redis://localhost:6380"


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_settings():
    """Mock settings for testing"""
    with patch('app.core.config.settings') as mock_settings:
        mock_settings.SECRET_KEY = "test_secret_key_for_testing_only"
        mock_settings.DATABASE_URL = "postgresql+asyncpg://test:test@localhost:5433/test_db"
        mock_settings.REDIS_URL = "redis://localhost:6380"
        mock_settings.ENVIRONMENT = "test"
        yield mock_settings


@pytest.fixture
def mock_logger():
    """Mock structured logger"""
    return MagicMock()


# Import patch after setting environment variables
from unittest.mock import patch