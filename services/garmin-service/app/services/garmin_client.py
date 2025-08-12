from garminconnect import Garmin
import structlog
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from tenacity import retry, stop_after_attempt, wait_exponential
import asyncio
from functools import wraps

logger = structlog.get_logger(__name__)

def async_retry(func):
    """Decorator to add retry logic to async functions"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        return await asyncio.get_event_loop().run_in_executor(
            None, func, *args, **kwargs
        )
    return wrapper

class GarminClient:
    """Garmin Connect client wrapper"""
    
    def __init__(self):
        self.client: Optional[Garmin] = None
        self._authenticated = False

    async def authenticate(self, username: str, password: str) -> bool:
        """Authenticate with Garmin Connect"""
        try:
            # Run authentication in thread pool since garminconnect is sync
            self.client = await asyncio.get_event_loop().run_in_executor(
                None, lambda: Garmin(username, password)
            )
            
            # Test authentication by getting user summary
            await asyncio.get_event_loop().run_in_executor(
                None, self.client.get_user_summary, datetime.now().strftime("%Y-%m-%d")
            )
            
            self._authenticated = True
            logger.info("Successfully authenticated with Garmin Connect", username=username)
            return True
            
        except Exception as e:
            logger.error("Failed to authenticate with Garmin Connect", error=str(e), username=username)
            self._authenticated = False
            return False

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def get_activities(self, start_date: datetime, limit: int = 100) -> List[Dict[str, Any]]:
        """Get activities from Garmin Connect"""
        if not self._authenticated:
            raise ValueError("Not authenticated with Garmin Connect")

        try:
            activities = await asyncio.get_event_loop().run_in_executor(
                None, self.client.get_activities, 0, limit
            )
            
            # Filter activities by start date
            filtered_activities = []
            for activity in activities:
                activity_date = datetime.fromisoformat(activity['startTimeLocal'].replace('Z', '+00:00'))
                if activity_date >= start_date:
                    filtered_activities.append(activity)
            
            logger.info(f"Retrieved {len(filtered_activities)} activities from Garmin Connect")
            return filtered_activities
            
        except Exception as e:
            logger.error("Failed to get activities from Garmin Connect", error=str(e))
            raise

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def get_heart_rate_data(self, date: datetime) -> Dict[str, Any]:
        """Get heart rate data for a specific date"""
        if not self._authenticated:
            raise ValueError("Not authenticated with Garmin Connect")

        try:
            date_str = date.strftime("%Y-%m-%d")
            hr_data = await asyncio.get_event_loop().run_in_executor(
                None, self.client.get_heart_rate, date_str
            )
            
            logger.info(f"Retrieved heart rate data for {date_str}")
            return hr_data
            
        except Exception as e:
            logger.error("Failed to get heart rate data", error=str(e), date=date.strftime("%Y-%m-%d"))
            raise

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def get_sleep_data(self, date: datetime) -> Dict[str, Any]:
        """Get sleep data for a specific date"""
        if not self._authenticated:
            raise ValueError("Not authenticated with Garmin Connect")

        try:
            date_str = date.strftime("%Y-%m-%d")
            sleep_data = await asyncio.get_event_loop().run_in_executor(
                None, self.client.get_sleep_data, date_str
            )
            
            logger.info(f"Retrieved sleep data for {date_str}")
            return sleep_data
            
        except Exception as e:
            logger.error("Failed to get sleep data", error=str(e), date=date.strftime("%Y-%m-%d"))
            raise

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def get_body_composition(self, date: datetime) -> Dict[str, Any]:
        """Get body composition data for a specific date"""
        if not self._authenticated:
            raise ValueError("Not authenticated with Garmin Connect")

        try:
            date_str = date.strftime("%Y-%m-%d")
            # Get user stats which includes weight data
            stats = await asyncio.get_event_loop().run_in_executor(
                None, self.client.get_user_summary, date_str
            )
            
            logger.info(f"Retrieved body composition data for {date_str}")
            return stats
            
        except Exception as e:
            logger.error("Failed to get body composition data", error=str(e), date=date.strftime("%Y-%m-%d"))
            raise

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def get_stress_data(self, date: datetime) -> Dict[str, Any]:
        """Get stress data for a specific date"""
        if not self._authenticated:
            raise ValueError("Not authenticated with Garmin Connect")

        try:
            date_str = date.strftime("%Y-%m-%d")
            stress_data = await asyncio.get_event_loop().run_in_executor(
                None, self.client.get_stress_data, date_str
            )
            
            logger.info(f"Retrieved stress data for {date_str}")
            return stress_data
            
        except Exception as e:
            logger.error("Failed to get stress data", error=str(e), date=date.strftime("%Y-%m-%d"))
            raise

# Global client instance
garmin_client = GarminClient()