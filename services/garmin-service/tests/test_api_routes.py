"""
Integration tests for API routes
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
import uuid
from datetime import datetime, date, timedelta

from app.main import app


@pytest.fixture
def mock_db_session():
    """Create a mock database session"""
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def sample_user_id():
    """Sample user ID for testing"""
    return str(uuid.uuid4())


@pytest.fixture
async def client():
    """Create an async test client"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


class TestCredentialsEndpoints:
    """Test credential management endpoints"""
    
    @pytest.mark.asyncio
    async def test_store_credentials_success(self, client, sample_user_id):
        """Test successful credential storage"""
        credentials_data = {
            "username": "test_user",
            "password": "test_password"
        }
        
        with patch('app.api.routes.credential_service') as mock_service, \
             patch('app.api.routes.get_db'):
            
            mock_service.test_credentials = AsyncMock(return_value=True)
            mock_service.store_credentials = AsyncMock(return_value=True)
            
            response = await client.post(
                f"/credentials?user_id={sample_user_id}",
                json=credentials_data
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["message"] == "Credentials stored successfully"
            assert data["user_id"] == sample_user_id
            
            mock_service.test_credentials.assert_called_once_with("test_user", "test_password")
            mock_service.store_credentials.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_store_credentials_invalid_credentials(self, client, sample_user_id):
        """Test storing invalid credentials"""
        credentials_data = {
            "username": "invalid_user",
            "password": "invalid_password"
        }
        
        with patch('app.api.routes.credential_service') as mock_service, \
             patch('app.api.routes.get_db'):
            
            mock_service.test_credentials = AsyncMock(return_value=False)
            
            response = await client.post(
                f"/credentials?user_id={sample_user_id}",
                json=credentials_data
            )
            
            assert response.status_code == 401
            data = response.json()
            assert data["detail"] == "Invalid Garmin Connect credentials"
    
    @pytest.mark.asyncio
    async def test_store_credentials_storage_failure(self, client, sample_user_id):
        """Test credential storage failure"""
        credentials_data = {
            "username": "test_user",
            "password": "test_password"
        }
        
        with patch('app.api.routes.credential_service') as mock_service, \
             patch('app.api.routes.get_db'):
            
            mock_service.test_credentials = AsyncMock(return_value=True)
            mock_service.store_credentials = AsyncMock(return_value=False)
            
            response = await client.post(
                f"/credentials?user_id={sample_user_id}",
                json=credentials_data
            )
            
            assert response.status_code == 500
            data = response.json()
            assert data["detail"] == "Failed to store credentials"
    
    @pytest.mark.asyncio
    async def test_delete_credentials_success(self, client, sample_user_id):
        """Test successful credential deletion"""
        with patch('app.api.routes.credential_service') as mock_service, \
             patch('app.api.routes.get_db'):
            
            mock_service.delete_credentials = AsyncMock(return_value=True)
            
            response = await client.delete(f"/credentials?user_id={sample_user_id}")
            
            assert response.status_code == 200
            data = response.json()
            assert data["message"] == "Credentials deleted successfully"
            assert data["user_id"] == sample_user_id
    
    @pytest.mark.asyncio
    async def test_delete_credentials_not_found(self, client, sample_user_id):
        """Test deleting non-existent credentials"""
        with patch('app.api.routes.credential_service') as mock_service, \
             patch('app.api.routes.get_db'):
            
            mock_service.delete_credentials = AsyncMock(return_value=False)
            
            response = await client.delete(f"/credentials?user_id={sample_user_id}")
            
            assert response.status_code == 200
            data = response.json()
            assert data["message"] == "No credentials found to delete"
    
    @pytest.mark.asyncio
    async def test_credentials_missing_user_id(self, client):
        """Test credentials endpoints without user_id"""
        credentials_data = {
            "username": "test_user",
            "password": "test_password"
        }
        
        response = await client.post("/credentials", json=credentials_data)
        assert response.status_code == 422  # Validation error
        
        response = await client.delete("/credentials")
        assert response.status_code == 422  # Validation error


class TestSyncEndpoint:
    """Test data synchronization endpoint"""
    
    @pytest.mark.asyncio
    async def test_sync_success(self, client, sample_user_id):
        """Test successful data synchronization"""
        with patch('app.api.routes.credential_service') as mock_cred_service, \
             patch('app.api.routes.GarminClient') as MockClient, \
             patch('app.api.routes.GarminDataNormalizer') as MockNormalizer, \
             patch('app.api.routes.get_db') as mock_get_db:
            
            # Mock credentials
            mock_cred_service.get_credentials = AsyncMock(return_value={
                "username": "test_user",
                "password": "test_password"
            })
            
            # Mock Garmin client
            mock_client = MockClient.return_value
            mock_client.authenticate = AsyncMock(return_value=True)
            mock_client.get_activities = AsyncMock(return_value=[
                {"activityId": "123", "activityName": "Test Run"}
            ])
            mock_client.get_heart_rate_data = AsyncMock(return_value={"restingHeartRate": 65})
            mock_client.get_sleep_data = AsyncMock(return_value=None)
            mock_client.get_body_composition = AsyncMock(return_value=None)
            mock_client.get_stress_data = AsyncMock(return_value=None)
            
            # Mock normalizer
            MockNormalizer.normalize_activities_batch.return_value = [
                {"activity_id": "123", "activity_name": "Test Run"}
            ]
            MockNormalizer.normalize_heart_rate_data.return_value = {
                "metric_type": "heart_rate",
                "recorded_date": datetime.now(),
                "metric_data": {"restingHeartRate": 65}
            }
            
            # Mock database
            mock_db = AsyncMock()
            mock_db.execute.return_value.scalar_one_or_none.return_value = None  # No existing data
            mock_get_db.return_value = mock_db
            
            response = await client.post(f"/sync?user_id={sample_user_id}&days=7")
            
            assert response.status_code == 200
            data = response.json()
            assert data["message"] == "Garmin data sync completed"
            assert data["user_id"] == sample_user_id
            assert data["sync_period_days"] == 7
            assert "activities_synced" in data
            assert "health_metrics_synced" in data
    
    @pytest.mark.asyncio
    async def test_sync_no_credentials(self, client, sample_user_id):
        """Test sync without stored credentials"""
        with patch('app.api.routes.credential_service') as mock_service, \
             patch('app.api.routes.get_db'):
            
            mock_service.get_credentials = AsyncMock(return_value=None)
            
            response = await client.post(f"/sync?user_id={sample_user_id}")
            
            assert response.status_code == 404
            data = response.json()
            assert "No Garmin credentials found" in data["detail"]
    
    @pytest.mark.asyncio
    async def test_sync_authentication_failure(self, client, sample_user_id):
        """Test sync with authentication failure"""
        with patch('app.api.routes.credential_service') as mock_cred_service, \
             patch('app.api.routes.GarminClient') as MockClient, \
             patch('app.api.routes.get_db'):
            
            mock_cred_service.get_credentials = AsyncMock(return_value={
                "username": "test_user",
                "password": "test_password"
            })
            
            mock_client = MockClient.return_value
            mock_client.authenticate = AsyncMock(return_value=False)
            
            response = await client.post(f"/sync?user_id={sample_user_id}")
            
            assert response.status_code == 401
            data = response.json()
            assert "Failed to authenticate with Garmin Connect" in data["detail"]
    
    @pytest.mark.asyncio
    async def test_sync_with_custom_days(self, client, sample_user_id):
        """Test sync with custom number of days"""
        with patch('app.api.routes.credential_service') as mock_cred_service, \
             patch('app.api.routes.GarminClient') as MockClient, \
             patch('app.api.routes.GarminDataNormalizer') as MockNormalizer, \
             patch('app.api.routes.get_db') as mock_get_db:
            
            # Setup mocks similar to test_sync_success
            mock_cred_service.get_credentials = AsyncMock(return_value={
                "username": "test_user", "password": "test_password"
            })
            
            mock_client = MockClient.return_value
            mock_client.authenticate = AsyncMock(return_value=True)
            mock_client.get_activities = AsyncMock(return_value=[])
            mock_client.get_heart_rate_data = AsyncMock(return_value=None)
            mock_client.get_sleep_data = AsyncMock(return_value=None)
            mock_client.get_body_composition = AsyncMock(return_value=None)
            mock_client.get_stress_data = AsyncMock(return_value=None)
            
            MockNormalizer.normalize_activities_batch.return_value = []
            
            mock_db = AsyncMock()
            mock_get_db.return_value = mock_db
            
            response = await client.post(f"/sync?user_id={sample_user_id}&days=14")
            
            assert response.status_code == 200
            data = response.json()
            assert data["sync_period_days"] == 14


class TestActivitiesEndpoint:
    """Test activities retrieval endpoint"""
    
    @pytest.mark.asyncio
    async def test_get_activities_success(self, client, sample_user_id):
        """Test successful activities retrieval"""
        mock_activities = [
            MagicMock(
                id=uuid.uuid4(),
                activity_id="123",
                activity_name="Morning Run",
                activity_type="running",
                start_time=datetime.now(),
                duration_seconds=3600,
                distance_meters=10000,
                calories=450,
                avg_heart_rate=145,
                max_heart_rate=170
            ),
            MagicMock(
                id=uuid.uuid4(),
                activity_id="456",
                activity_name="Evening Walk",
                activity_type="walking",
                start_time=datetime.now() - timedelta(days=1),
                duration_seconds=2400,
                distance_meters=5000,
                calories=200,
                avg_heart_rate=120,
                max_heart_rate=140
            )
        ]
        
        with patch('app.api.routes.get_db') as mock_get_db:
            mock_db = AsyncMock()
            mock_db.execute.return_value.scalars.return_value.all.return_value = mock_activities
            mock_get_db.return_value = mock_db
            
            response = await client.get(f"/activities?user_id={sample_user_id}&days=7")
            
            assert response.status_code == 200
            data = response.json()
            assert data["count"] == 2
            assert data["period_days"] == 7
            assert data["user_id"] == sample_user_id
            assert len(data["activities"]) == 2
            assert data["activities"][0]["name"] == "Morning Run"
            assert data["activities"][1]["name"] == "Evening Walk"
    
    @pytest.mark.asyncio
    async def test_get_activities_with_type_filter(self, client, sample_user_id):
        """Test activities retrieval with activity type filter"""
        with patch('app.api.routes.get_db') as mock_get_db:
            mock_db = AsyncMock()
            mock_db.execute.return_value.scalars.return_value.all.return_value = []
            mock_get_db.return_value = mock_db
            
            response = await client.get(
                f"/activities?user_id={sample_user_id}&days=7&activity_type=running"
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["activity_type_filter"] == "running"
    
    @pytest.mark.asyncio
    async def test_get_activities_with_limit(self, client, sample_user_id):
        """Test activities retrieval with limit parameter"""
        with patch('app.api.routes.get_db') as mock_get_db:
            mock_db = AsyncMock()
            mock_db.execute.return_value.scalars.return_value.all.return_value = []
            mock_get_db.return_value = mock_db
            
            response = await client.get(
                f"/activities?user_id={sample_user_id}&limit=50"
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["count"] == 0
    
    @pytest.mark.asyncio
    async def test_get_activities_validation_error(self, client, sample_user_id):
        """Test activities endpoint with invalid parameters"""
        # Test invalid limit (too high)
        response = await client.get(
            f"/activities?user_id={sample_user_id}&limit=1000"
        )
        assert response.status_code == 422
        
        # Test invalid days (negative)
        response = await client.get(
            f"/activities?user_id={sample_user_id}&days=0"
        )
        assert response.status_code == 422


class TestHealthMetricsEndpoints:
    """Test health metrics endpoints"""
    
    @pytest.mark.asyncio
    async def test_get_health_metrics_success(self, client, sample_user_id):
        """Test successful health metrics retrieval"""
        mock_metrics = [
            MagicMock(
                id=uuid.uuid4(),
                metric_type="heart_rate",
                recorded_date=date.today(),
                metric_data={"restingHeartRate": 65},
                processed_at=datetime.now()
            )
        ]
        
        with patch('app.api.routes.get_db') as mock_get_db:
            mock_db = AsyncMock()
            mock_db.execute.return_value.scalars.return_value.all.return_value = mock_metrics
            mock_get_db.return_value = mock_db
            
            response = await client.get(
                f"/health/heart_rate?user_id={sample_user_id}&days=7"
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["metric_type"] == "heart_rate"
            assert data["count"] == 1
            assert data["period_days"] == 7
            assert len(data["metrics"]) == 1
    
    @pytest.mark.asyncio
    async def test_get_health_metrics_invalid_type(self, client, sample_user_id):
        """Test health metrics endpoint with invalid metric type"""
        response = await client.get(
            f"/health/invalid_metric?user_id={sample_user_id}"
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "Invalid metric type" in data["detail"]
    
    @pytest.mark.asyncio
    async def test_get_health_metrics_valid_types(self, client, sample_user_id):
        """Test all valid metric types"""
        valid_types = ['heart_rate', 'sleep', 'body_composition', 'stress']
        
        with patch('app.api.routes.get_db') as mock_get_db:
            mock_db = AsyncMock()
            mock_db.execute.return_value.scalars.return_value.all.return_value = []
            mock_get_db.return_value = mock_db
            
            for metric_type in valid_types:
                response = await client.get(
                    f"/health/{metric_type}?user_id={sample_user_id}"
                )
                assert response.status_code == 200
                data = response.json()
                assert data["metric_type"] == metric_type
    
    @pytest.mark.asyncio
    async def test_get_health_summary_success(self, client, sample_user_id):
        """Test successful health summary retrieval"""
        mock_metrics = [
            MagicMock(
                metric_type="heart_rate",
                recorded_date=date.today(),
                metric_data={"restingHeartRate": 65}
            ),
            MagicMock(
                metric_type="sleep",
                recorded_date=date.today() - timedelta(days=1),
                metric_data={"sleepTimeSeconds": 28800}
            )
        ]
        
        with patch('app.api.routes.get_db') as mock_get_db:
            mock_db = AsyncMock()
            mock_db.execute.return_value.scalars.return_value.all.return_value = mock_metrics
            mock_get_db.return_value = mock_db
            
            response = await client.get(f"/health/summary?user_id={sample_user_id}")
            
            assert response.status_code == 200
            data = response.json()
            assert data["user_id"] == sample_user_id
            assert data["total_metrics"] == 2
            assert "summary" in data
            assert len(data["summary"]) == 2  # heart_rate and sleep
    
    @pytest.mark.asyncio
    async def test_get_health_summary_custom_days(self, client, sample_user_id):
        """Test health summary with custom number of days"""
        with patch('app.api.routes.get_db') as mock_get_db:
            mock_db = AsyncMock()
            mock_db.execute.return_value.scalars.return_value.all.return_value = []
            mock_get_db.return_value = mock_db
            
            response = await client.get(
                f"/health/summary?user_id={sample_user_id}&days=14"
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["period_days"] == 14


class TestSyncStatusEndpoint:
    """Test sync status endpoint"""
    
    @pytest.mark.asyncio
    async def test_get_sync_status_with_credentials(self, client, sample_user_id):
        """Test sync status when user has credentials"""
        mock_activity = MagicMock(processed_at=datetime.now())
        mock_health_metric = MagicMock(processed_at=datetime.now())
        
        with patch('app.api.routes.credential_service') as mock_service, \
             patch('app.api.routes.get_db') as mock_get_db:
            
            mock_service.get_credentials = AsyncMock(return_value={"username": "test"})
            
            mock_db = AsyncMock()
            # Mock database queries for latest data and counts
            mock_db.execute.return_value.scalar_one_or_none.side_effect = [
                mock_activity, mock_health_metric
            ]
            mock_db.execute.return_value.scalars.return_value.all.side_effect = [
                [mock_activity, mock_activity],  # 2 activities
                [mock_health_metric]  # 1 health metric
            ]
            mock_get_db.return_value = mock_db
            
            response = await client.get(f"/sync/status?user_id={sample_user_id}")
            
            assert response.status_code == 200
            data = response.json()
            assert data["user_id"] == sample_user_id
            assert data["credentials_configured"] is True
            assert data["sync_ready"] is True
            assert data["total_activities"] == 2
            assert data["total_health_metrics"] == 1
            assert data["latest_activity_sync"] is not None
            assert data["latest_health_sync"] is not None
    
    @pytest.mark.asyncio
    async def test_get_sync_status_without_credentials(self, client, sample_user_id):
        """Test sync status when user has no credentials"""
        with patch('app.api.routes.credential_service') as mock_service, \
             patch('app.api.routes.get_db') as mock_get_db:
            
            mock_service.get_credentials = AsyncMock(return_value=None)
            
            mock_db = AsyncMock()
            mock_db.execute.return_value.scalar_one_or_none.return_value = None
            mock_db.execute.return_value.scalars.return_value.all.return_value = []
            mock_get_db.return_value = mock_db
            
            response = await client.get(f"/sync/status?user_id={sample_user_id}")
            
            assert response.status_code == 200
            data = response.json()
            assert data["credentials_configured"] is False
            assert data["sync_ready"] is False
            assert data["total_activities"] == 0
            assert data["total_health_metrics"] == 0
            assert data["latest_activity_sync"] is None
            assert data["latest_health_sync"] is None


class TestErrorHandling:
    """Test error handling in API endpoints"""
    
    @pytest.mark.asyncio
    async def test_database_error_handling(self, client, sample_user_id):
        """Test that database errors are properly handled"""
        with patch('app.api.routes.get_db') as mock_get_db:
            mock_db = AsyncMock()
            mock_db.execute.side_effect = Exception("Database connection failed")
            mock_get_db.return_value = mock_db
            
            response = await client.get(f"/activities?user_id={sample_user_id}")
            
            assert response.status_code == 500
            data = response.json()
            assert "Failed to get activities" in data["detail"]
    
    @pytest.mark.asyncio
    async def test_sync_rollback_on_error(self, client, sample_user_id):
        """Test that sync operations rollback on error"""
        with patch('app.api.routes.credential_service') as mock_cred_service, \
             patch('app.api.routes.GarminClient') as MockClient, \
             patch('app.api.routes.get_db') as mock_get_db:
            
            mock_cred_service.get_credentials = AsyncMock(return_value={
                "username": "test_user", "password": "test_password"
            })
            
            mock_client = MockClient.return_value
            mock_client.authenticate = AsyncMock(return_value=True)
            mock_client.get_activities = AsyncMock(side_effect=Exception("API Error"))
            
            mock_db = AsyncMock()
            mock_get_db.return_value = mock_db
            
            response = await client.post(f"/sync?user_id={sample_user_id}")
            
            assert response.status_code == 500
            mock_db.rollback.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_missing_required_parameters(self, client):
        """Test endpoints with missing required parameters"""
        # Test endpoints that require user_id
        endpoints = [
            "/activities",
            "/health/heart_rate",
            "/health/summary",
            "/sync/status"
        ]
        
        for endpoint in endpoints:
            response = await client.get(endpoint)
            assert response.status_code == 422  # Validation error