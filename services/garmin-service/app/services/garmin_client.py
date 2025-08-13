from garminconnect import Garmin
import structlog
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta, date
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import asyncio
from functools import wraps
import time
import redis.asyncio as redis
from app.core.config import settings

logger = structlog.get_logger(__name__)

class RateLimiter:
    """Rate limiter using Redis for distributed rate limiting"""
    
    def __init__(self, redis_url: str):
        self.redis_url = redis_url
        self._redis = None
    
    async def get_redis(self):
        if self._redis is None:
            self._redis = redis.from_url(self.redis_url)
        return self._redis
    
    async def is_allowed(self, key: str, limit: int, window: int) -> bool:
        """Check if request is allowed under rate limit"""
        redis = await self.get_redis()
        current_time = int(time.time())
        window_start = current_time - window
        
        # Clean old entries and count current requests
        pipe = redis.pipeline()
        pipe.zremrangebyscore(key, 0, window_start)
        pipe.zcard(key)
        pipe.zadd(key, {str(current_time): current_time})
        pipe.expire(key, window)
        
        results = await pipe.execute()
        current_count = results[1]
        
        return current_count < limit

# Global rate limiter
rate_limiter = RateLimiter(settings.REDIS_URL)

def async_retry(func):
    """Decorator to add retry logic to async functions"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        return await asyncio.get_event_loop().run_in_executor(
            None, func, *args, **kwargs
        )
    return wrapper

class GarminClient:
    """Garmin Connect client wrapper with rate limiting and error handling"""
    
    def __init__(self, user_id: str = None):
        self.client: Optional[Garmin] = None
        self._authenticated = False
        self.user_id = user_id
        self._last_request_time = 0
        self._min_request_interval = 1.0  # Minimum 1 second between requests

    async def _rate_limit_check(self) -> bool:
        """Check rate limiting before making requests"""
        if self.user_id:
            rate_key = f"garmin_requests:{self.user_id}"
            return await rate_limiter.is_allowed(rate_key, limit=60, window=60)  # 60 requests per minute
        return True

    async def _wait_for_rate_limit(self):
        """Wait if needed to respect rate limiting"""
        current_time = time.time()
        time_since_last = current_time - self._last_request_time
        if time_since_last < self._min_request_interval:
            wait_time = self._min_request_interval - time_since_last
            await asyncio.sleep(wait_time)
        self._last_request_time = time.time()

    async def authenticate(self, username: str, password: str) -> bool:
        """Authenticate with Garmin Connect"""
        try:
            if not await self._rate_limit_check():
                logger.warning("Rate limit exceeded for authentication", user_id=self.user_id)
                return False

            await self._wait_for_rate_limit()
            
            # Run authentication in thread pool since garminconnect is sync
            self.client = await asyncio.get_event_loop().run_in_executor(
                None, lambda: Garmin(username, password)
            )
            
            # Test authentication by getting user summary
            await asyncio.get_event_loop().run_in_executor(
                None, self.client.get_user_summary, datetime.now().strftime("%Y-%m-%d")
            )
            
            self._authenticated = True
            logger.info("Successfully authenticated with Garmin Connect", 
                       username=username, user_id=self.user_id)
            return True
            
        except Exception as e:
            logger.error("Failed to authenticate with Garmin Connect", 
                        error=str(e), username=username, user_id=self.user_id)
            self._authenticated = False
            return False

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10),
           retry=retry_if_exception_type((ConnectionError, TimeoutError)))
    async def get_activities(self, start_date: datetime, limit: int = 100) -> List[Dict[str, Any]]:
        """Get activities from Garmin Connect"""
        if not self._authenticated:
            raise ValueError("Not authenticated with Garmin Connect")

        if not await self._rate_limit_check():
            raise Exception("Rate limit exceeded")

        try:
            await self._wait_for_rate_limit()
            
            activities = await asyncio.get_event_loop().run_in_executor(
                None, self.client.get_activities, 0, limit
            )
            
            # Filter activities by start date
            filtered_activities = []
            for activity in activities:
                try:
                    activity_date = datetime.fromisoformat(activity['startTimeLocal'].replace('Z', '+00:00'))
                    if activity_date >= start_date:
                        filtered_activities.append(activity)
                except (KeyError, ValueError) as e:
                    logger.warning("Invalid activity data", activity_id=activity.get('activityId'), error=str(e))
                    continue
            
            logger.info(f"Retrieved {len(filtered_activities)} activities from Garmin Connect", 
                       user_id=self.user_id, total_fetched=len(activities))
            return filtered_activities
            
        except Exception as e:
            logger.error("Failed to get activities from Garmin Connect", 
                        error=str(e), user_id=self.user_id)
            raise

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10),
           retry=retry_if_exception_type((ConnectionError, TimeoutError)))
    async def get_heart_rate_data(self, target_date: date) -> Optional[Dict[str, Any]]:
        """Get heart rate data for a specific date"""
        if not self._authenticated:
            raise ValueError("Not authenticated with Garmin Connect")

        if not await self._rate_limit_check():
            raise Exception("Rate limit exceeded")

        try:
            await self._wait_for_rate_limit()
            
            date_str = target_date.strftime("%Y-%m-%d")
            hr_data = await asyncio.get_event_loop().run_in_executor(
                None, self.client.get_heart_rate, date_str
            )
            
            logger.info(f"Retrieved heart rate data for {date_str}", user_id=self.user_id)
            return hr_data
            
        except Exception as e:
            logger.error("Failed to get heart rate data", 
                        error=str(e), date=target_date.strftime("%Y-%m-%d"), user_id=self.user_id)
            return None

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10),
           retry=retry_if_exception_type((ConnectionError, TimeoutError)))
    async def get_sleep_data(self, target_date: date) -> Optional[Dict[str, Any]]:
        """Get sleep data for a specific date"""
        if not self._authenticated:
            raise ValueError("Not authenticated with Garmin Connect")

        if not await self._rate_limit_check():
            raise Exception("Rate limit exceeded")

        try:
            await self._wait_for_rate_limit()
            
            date_str = target_date.strftime("%Y-%m-%d")
            sleep_data = await asyncio.get_event_loop().run_in_executor(
                None, self.client.get_sleep_data, date_str
            )
            
            logger.info(f"Retrieved sleep data for {date_str}", user_id=self.user_id)
            return sleep_data
            
        except Exception as e:
            logger.error("Failed to get sleep data", 
                        error=str(e), date=target_date.strftime("%Y-%m-%d"), user_id=self.user_id)
            return None

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10),
           retry=retry_if_exception_type((ConnectionError, TimeoutError)))
    async def get_body_composition(self, target_date: date) -> Optional[Dict[str, Any]]:
        """Get body composition data for a specific date"""
        if not self._authenticated:
            raise ValueError("Not authenticated with Garmin Connect")

        if not await self._rate_limit_check():
            raise Exception("Rate limit exceeded")

        try:
            await self._wait_for_rate_limit()
            
            date_str = target_date.strftime("%Y-%m-%d")
            # Get user stats which includes weight data
            stats = await asyncio.get_event_loop().run_in_executor(
                None, self.client.get_user_summary, date_str
            )
            
            logger.info(f"Retrieved body composition data for {date_str}", user_id=self.user_id)
            return stats
            
        except Exception as e:
            logger.error("Failed to get body composition data", 
                        error=str(e), date=target_date.strftime("%Y-%m-%d"), user_id=self.user_id)
            return None

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10),
           retry=retry_if_exception_type((ConnectionError, TimeoutError)))
    async def get_stress_data(self, target_date: date) -> Optional[Dict[str, Any]]:
        """Get stress data for a specific date"""
        if not self._authenticated:
            raise ValueError("Not authenticated with Garmin Connect")

        if not await self._rate_limit_check():
            raise Exception("Rate limit exceeded")

        try:
            await self._wait_for_rate_limit()
            
            date_str = target_date.strftime("%Y-%m-%d")
            stress_data = await asyncio.get_event_loop().run_in_executor(
                None, self.client.get_stress_data, date_str
            )
            
            logger.info(f"Retrieved stress data for {date_str}", user_id=self.user_id)
            return stress_data
            
        except Exception as e:
            logger.error("Failed to get stress data", 
                        error=str(e), date=target_date.strftime("%Y-%m-%d"), user_id=self.user_id)
            return None