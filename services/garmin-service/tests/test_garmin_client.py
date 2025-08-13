"""
Unit tests for Garmin client
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, date, timedelta
import redis.asyncio as redis

from app.services.garmin_client import GarminClient, RateLimiter


@pytest.fixture
def mock_redis():
    """Create a mock Redis connection"""
    return AsyncMock(spec=redis.Redis)


@pytest.fixture
def rate_limiter(mock_redis):
    """Create a rate limiter with mock Redis"""
    with patch('app.services.garmin_client.redis.from_url', return_value=mock_redis):
        return RateLimiter("redis://localhost:6379")


class TestRateLimiter:
    """Test rate limiting functionality"""
    
    @pytest.mark.asyncio
    async def test_is_allowed_under_limit(self, rate_limiter, mock_redis):
        """Test rate limiting when under the limit"""
        # Mock Redis pipeline
        mock_pipe = MagicMock()
        mock_pipe.execute = AsyncMock(return_value=[None, 5, None, None])  # Current count: 5
        mock_redis.pipeline.return_value = mock_pipe
        
        result = await rate_limiter.is_allowed("test_key", limit=10, window=60)
        
        assert result is True
        mock_redis.pipeline.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_is_allowed_over_limit(self, rate_limiter, mock_redis):
        """Test rate limiting when over the limit"""
        # Mock Redis pipeline
        mock_pipe = MagicMock()
        mock_pipe.execute = AsyncMock(return_value=[None, 15, None, None])  # Current count: 15
        mock_redis.pipeline.return_value = mock_pipe
        
        result = await rate_limiter.is_allowed("test_key", limit=10, window=60)
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_redis_connection_caching(self, rate_limiter):
        """Test that Redis connection is cached"""
        with patch('app.services.garmin_client.redis.from_url') as mock_from_url:
            mock_redis_conn = AsyncMock()
            mock_from_url.return_value = mock_redis_conn
            
            # First call should create connection
            conn1 = await rate_limiter.get_redis()
            # Second call should reuse connection
            conn2 = await rate_limiter.get_redis()
            
            assert conn1 is conn2
            mock_from_url.assert_called_once()


class TestGarminClient:
    """Test Garmin client functionality"""
    
    def test_client_initialization(self):
        """Test client initialization"""
        client = GarminClient(user_id="test_user_123")
        
        assert client.user_id == "test_user_123"
        assert client.client is None
        assert client._authenticated is False
        assert client._min_request_interval == 1.0
    
    @pytest.mark.asyncio
    async def test_rate_limit_check_with_user_id(self):
        """Test rate limit checking with user ID"""
        with patch('app.services.garmin_client.rate_limiter') as mock_rate_limiter:
            mock_rate_limiter.is_allowed = AsyncMock(return_value=True)
            
            client = GarminClient(user_id="test_user")
            result = await client._rate_limit_check()
            
            assert result is True
            mock_rate_limiter.is_allowed.assert_called_once_with(
                "garmin_requests:test_user", limit=60, window=60
            )
    
    @pytest.mark.asyncio
    async def test_rate_limit_check_without_user_id(self):
        """Test rate limit checking without user ID"""
        client = GarminClient()
        result = await client._rate_limit_check()
        
        assert result is True  # Should allow when no user_id
    
    @pytest.mark.asyncio
    async def test_wait_for_rate_limit(self):
        """Test rate limiting wait functionality"""
        client = GarminClient()
        client._last_request_time = 0  # Set to 0 to force wait
        
        with patch('asyncio.sleep') as mock_sleep:
            with patch('time.time', side_effect=[0.5, 1.5]):  # Current time, then after sleep
                await client._wait_for_rate_limit()
                
                mock_sleep.assert_called_once()
                assert mock_sleep.call_args[0][0] >= 0.5  # Should wait at least 0.5 seconds


class TestGarminAuthentication:
    """Test Garmin authentication"""
    
    @pytest.mark.asyncio
    async def test_successful_authentication(self):
        """Test successful Garmin authentication"""
        client = GarminClient(user_id="test_user")
        
        with patch.object(client, '_rate_limit_check', return_value=True), \
             patch.object(client, '_wait_for_rate_limit'), \
             patch('asyncio.get_event_loop') as mock_loop:
            
            # Mock the executor calls
            mock_executor = mock_loop.return_value.run_in_executor
            mock_garmin_instance = MagicMock()
            mock_executor.side_effect = [mock_garmin_instance, None]  # Constructor, then get_user_summary
            
            result = await client.authenticate("test_user", "test_pass")
            
            assert result is True
            assert client._authenticated is True
            assert client.client is mock_garmin_instance
            assert mock_executor.call_count == 2
    
    @pytest.mark.asyncio
    async def test_authentication_rate_limited(self):
        """Test authentication when rate limited"""
        client = GarminClient(user_id="test_user")
        
        with patch.object(client, '_rate_limit_check', return_value=False):
            result = await client.authenticate("test_user", "test_pass")
            
            assert result is False
            assert client._authenticated is False
    
    @pytest.mark.asyncio
    async def test_authentication_failure(self):
        """Test authentication failure"""
        client = GarminClient(user_id="test_user")
        
        with patch.object(client, '_rate_limit_check', return_value=True), \
             patch.object(client, '_wait_for_rate_limit'), \
             patch('asyncio.get_event_loop') as mock_loop:
            
            mock_loop.return_value.run_in_executor.side_effect = Exception("Auth failed")
            
            result = await client.authenticate("test_user", "test_pass")
            
            assert result is False
            assert client._authenticated is False


class TestGarminDataRetrieval:
    """Test Garmin data retrieval methods"""
    
    @pytest.mark.asyncio
    async def test_get_activities_success(self):
        """Test successful activity retrieval"""
        client = GarminClient(user_id="test_user")
        client._authenticated = True
        
        mock_activities = [
            {
                'activityId': 1,
                'startTimeLocal': '2024-01-15T10:00:00',
                'activityName': 'Morning Run'
            },
            {
                'activityId': 2,
                'startTimeLocal': '2024-01-14T08:00:00',  # Older than start_date
                'activityName': 'Yesterday Run'
            },
            {
                'activityId': 3,
                'startTimeLocal': '2024-01-16T09:00:00',
                'activityName': 'Another Run'
            }
        ]
        
        start_date = datetime(2024, 1, 15)
        
        with patch.object(client, '_rate_limit_check', return_value=True), \
             patch.object(client, '_wait_for_rate_limit'), \
             patch('asyncio.get_event_loop') as mock_loop:
            
            mock_loop.return_value.run_in_executor.return_value = mock_activities
            
            result = await client.get_activities(start_date, limit=100)
            
            # Should filter activities by start_date
            assert len(result) == 2
            assert result[0]['activityId'] == 1
            assert result[1]['activityId'] == 3
    
    @pytest.mark.asyncio
    async def test_get_activities_not_authenticated(self):
        """Test get_activities when not authenticated"""
        client = GarminClient()
        client._authenticated = False
        
        with pytest.raises(ValueError, match="Not authenticated"):
            await client.get_activities(datetime.now())
    
    @pytest.mark.asyncio
    async def test_get_activities_rate_limited(self):
        """Test get_activities when rate limited"""
        client = GarminClient()
        client._authenticated = True
        
        with patch.object(client, '_rate_limit_check', return_value=False):
            with pytest.raises(Exception, match="Rate limit exceeded"):
                await client.get_activities(datetime.now())
    
    @pytest.mark.asyncio
    async def test_get_activities_invalid_data(self):
        """Test get_activities with invalid activity data"""
        client = GarminClient()
        client._authenticated = True
        
        mock_activities = [
            {'activityId': 1, 'startTimeLocal': 'invalid-date'},  # Invalid date
            {'activityId': 2},  # Missing startTimeLocal
            {'activityId': 3, 'startTimeLocal': '2024-01-15T10:00:00'}  # Valid
        ]
        
        with patch.object(client, '_rate_limit_check', return_value=True), \
             patch.object(client, '_wait_for_rate_limit'), \
             patch('asyncio.get_event_loop') as mock_loop:
            
            mock_loop.return_value.run_in_executor.return_value = mock_activities
            
            result = await client.get_activities(datetime(2024, 1, 1))
            
            # Should only include valid activities
            assert len(result) == 1
            assert result[0]['activityId'] == 3
    
    @pytest.mark.asyncio
    async def test_get_heart_rate_data_success(self):
        """Test successful heart rate data retrieval"""
        client = GarminClient()
        client._authenticated = True
        
        mock_hr_data = {'restingHeartRate': 65, 'maxHeartRate': 180}
        target_date = date(2024, 1, 15)
        
        with patch.object(client, '_rate_limit_check', return_value=True), \
             patch.object(client, '_wait_for_rate_limit'), \
             patch('asyncio.get_event_loop') as mock_loop:
            
            mock_loop.return_value.run_in_executor.return_value = mock_hr_data
            
            result = await client.get_heart_rate_data(target_date)
            
            assert result == mock_hr_data
            # Verify correct date format passed to client
            mock_loop.return_value.run_in_executor.assert_called_once_with(
                None, client.client.get_heart_rate, "2024-01-15"
            )
    
    @pytest.mark.asyncio
    async def test_get_heart_rate_data_error(self):
        """Test heart rate data retrieval error"""
        client = GarminClient()
        client._authenticated = True
        
        with patch.object(client, '_rate_limit_check', return_value=True), \
             patch.object(client, '_wait_for_rate_limit'), \
             patch('asyncio.get_event_loop') as mock_loop:
            
            mock_loop.return_value.run_in_executor.side_effect = Exception("API Error")
            
            result = await client.get_heart_rate_data(date(2024, 1, 15))
            
            assert result is None
    
    @pytest.mark.asyncio
    async def test_get_sleep_data_success(self):
        """Test successful sleep data retrieval"""
        client = GarminClient()
        client._authenticated = True
        
        mock_sleep_data = {'sleepTimeSeconds': 28800, 'sleepEfficiency': 85}
        
        with patch.object(client, '_rate_limit_check', return_value=True), \
             patch.object(client, '_wait_for_rate_limit'), \
             patch('asyncio.get_event_loop') as mock_loop:
            
            mock_loop.return_value.run_in_executor.return_value = mock_sleep_data
            
            result = await client.get_sleep_data(date(2024, 1, 15))
            
            assert result == mock_sleep_data
    
    @pytest.mark.asyncio
    async def test_get_body_composition_success(self):
        """Test successful body composition data retrieval"""
        client = GarminClient()
        client._authenticated = True
        
        mock_body_data = {'weight': 75.5, 'bodyFat': 18.2}
        
        with patch.object(client, '_rate_limit_check', return_value=True), \
             patch.object(client, '_wait_for_rate_limit'), \
             patch('asyncio.get_event_loop') as mock_loop:
            
            mock_loop.return_value.run_in_executor.return_value = mock_body_data
            
            result = await client.get_body_composition(date(2024, 1, 15))
            
            assert result == mock_body_data
    
    @pytest.mark.asyncio
    async def test_get_stress_data_success(self):
        """Test successful stress data retrieval"""
        client = GarminClient()
        client._authenticated = True
        
        mock_stress_data = {'averageStressLevel': 25, 'maxStressLevel': 65}
        
        with patch.object(client, '_rate_limit_check', return_value=True), \
             patch.object(client, '_wait_for_rate_limit'), \
             patch('asyncio.get_event_loop') as mock_loop:
            
            mock_loop.return_value.run_in_executor.return_value = mock_stress_data
            
            result = await client.get_stress_data(date(2024, 1, 15))
            
            assert result == mock_stress_data


class TestRetryLogic:
    """Test retry logic in Garmin client"""
    
    @pytest.mark.asyncio
    async def test_get_activities_retry_on_connection_error(self):
        """Test that get_activities retries on connection errors"""
        client = GarminClient()
        client._authenticated = True
        
        with patch.object(client, '_rate_limit_check', return_value=True), \
             patch.object(client, '_wait_for_rate_limit'), \
             patch('asyncio.get_event_loop') as mock_loop:
            
            # First call fails with ConnectionError, second succeeds
            mock_loop.return_value.run_in_executor.side_effect = [
                ConnectionError("Connection failed"),
                []  # Success on retry
            ]
            
            result = await client.get_activities(datetime.now())
            
            assert result == []
            assert mock_loop.return_value.run_in_executor.call_count == 2
    
    @pytest.mark.asyncio
    async def test_retry_gives_up_after_max_attempts(self):
        """Test that retry gives up after maximum attempts"""
        client = GarminClient()
        client._authenticated = True
        
        with patch.object(client, '_rate_limit_check', return_value=True), \
             patch.object(client, '_wait_for_rate_limit'), \
             patch('asyncio.get_event_loop') as mock_loop:
            
            # Always fail with ConnectionError
            mock_loop.return_value.run_in_executor.side_effect = ConnectionError("Always fails")
            
            with pytest.raises(ConnectionError):
                await client.get_activities(datetime.now())
            
            # Should try 3 times (original + 2 retries)
            assert mock_loop.return_value.run_in_executor.call_count == 3


class TestErrorHandling:
    """Test error handling in Garmin client"""
    
    @pytest.mark.asyncio
    async def test_all_data_methods_require_authentication(self):
        """Test that all data methods require authentication"""
        client = GarminClient()
        client._authenticated = False
        
        methods_and_args = [
            (client.get_activities, (datetime.now(),)),
            (client.get_heart_rate_data, (date.today(),)),
            (client.get_sleep_data, (date.today(),)),
            (client.get_body_composition, (date.today(),)),
            (client.get_stress_data, (date.today(),)),
        ]
        
        for method, args in methods_and_args:
            with pytest.raises(ValueError, match="Not authenticated"):
                await method(*args)
    
    @pytest.mark.asyncio
    async def test_all_data_methods_respect_rate_limiting(self):
        """Test that all data methods respect rate limiting"""
        client = GarminClient()
        client._authenticated = True
        
        methods_and_args = [
            (client.get_activities, (datetime.now(),)),
            (client.get_heart_rate_data, (date.today(),)),
            (client.get_sleep_data, (date.today(),)),
            (client.get_body_composition, (date.today(),)),
            (client.get_stress_data, (date.today(),)),
        ]
        
        for method, args in methods_and_args:
            with patch.object(client, '_rate_limit_check', return_value=False):
                with pytest.raises(Exception, match="Rate limit exceeded"):
                    await method(*args)