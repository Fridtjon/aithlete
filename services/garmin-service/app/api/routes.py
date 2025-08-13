from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, insert, update
from datetime import datetime, timedelta, date
from typing import List, Optional, Dict, Any
import structlog
from pydantic import BaseModel

from app.core.database import get_db
from app.services.garmin_client import GarminClient
from app.services.credential_service import credential_service
from app.services.data_normalizer import GarminDataNormalizer
from app.models.garmin import GarminActivity, GarminHealthMetric
from app.models.user import UserCredential

logger = structlog.get_logger(__name__)
router = APIRouter()

# Pydantic models for request/response
class CredentialsRequest(BaseModel):
    username: str
    password: str

class SyncResponse(BaseModel):
    message: str
    activities_synced: int
    health_metrics_synced: int
    sync_period_days: int
    user_id: str

class ActivityResponse(BaseModel):
    id: str
    activity_id: str
    name: str
    type: Optional[str]
    start_time: Optional[str]
    duration_seconds: Optional[int]
    distance_meters: Optional[float]
    calories: Optional[int]
    avg_heart_rate: Optional[int]
    max_heart_rate: Optional[int]

class HealthMetricResponse(BaseModel):
    id: str
    metric_type: str
    recorded_date: str
    data: Dict[str, Any]
    processed_at: str

@router.post("/credentials")
async def store_credentials(
    user_id: str = Query(..., description="User ID"),
    credentials: CredentialsRequest = Body(...),
    db: AsyncSession = Depends(get_db)
):
    """Store encrypted Garmin credentials for a user"""
    try:
        # Test credentials first
        if not await credential_service.test_credentials(credentials.username, credentials.password):
            raise HTTPException(status_code=401, detail="Invalid Garmin Connect credentials")
        
        # Store encrypted credentials
        success = await credential_service.store_credentials(
            db, user_id, credentials.username, credentials.password
        )
        
        if success:
            return {"message": "Credentials stored successfully", "user_id": user_id}
        else:
            raise HTTPException(status_code=500, detail="Failed to store credentials")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to store credentials", error=str(e), user_id=user_id)
        raise HTTPException(status_code=500, detail=f"Failed to store credentials: {str(e)}")

@router.delete("/credentials")
async def delete_credentials(
    user_id: str = Query(..., description="User ID"),
    db: AsyncSession = Depends(get_db)
):
    """Delete Garmin credentials for a user"""
    try:
        success = await credential_service.delete_credentials(db, user_id)
        if success:
            return {"message": "Credentials deleted successfully", "user_id": user_id}
        else:
            return {"message": "No credentials found to delete", "user_id": user_id}
            
    except Exception as e:
        logger.error("Failed to delete credentials", error=str(e), user_id=user_id)
        raise HTTPException(status_code=500, detail=f"Failed to delete credentials: {str(e)}")

@router.post("/sync", response_model=SyncResponse)
async def sync_garmin_data(
    user_id: str = Query(..., description="User ID to sync data for"),
    days: int = Query(30, description="Number of days to sync"),
    db: AsyncSession = Depends(get_db)
):
    """Sync Garmin data for a user"""
    try:
        # Get stored credentials
        credentials = await credential_service.get_credentials(db, user_id)
        if not credentials:
            raise HTTPException(
                status_code=404, 
                detail="No Garmin credentials found. Please store credentials first using POST /credentials"
            )
        
        # Create client with user ID for rate limiting
        client = GarminClient(user_id=user_id)
        
        # Authenticate
        if not await client.authenticate(credentials["username"], credentials["password"]):
            raise HTTPException(status_code=401, detail="Failed to authenticate with Garmin Connect")
        
        start_date = datetime.now() - timedelta(days=days)
        
        # Sync activities
        logger.info("Starting activity sync", user_id=user_id, days=days)
        raw_activities = await client.get_activities(start_date)
        normalized_activities = GarminDataNormalizer.normalize_activities_batch(raw_activities)
        
        activity_count = 0
        for activity_data in normalized_activities:
            # Check if activity already exists
            result = await db.execute(
                select(GarminActivity).where(
                    GarminActivity.user_id == user_id,
                    GarminActivity.activity_id == activity_data["activity_id"]
                )
            )
            existing = result.scalar_one_or_none()
            
            if not existing and activity_data["activity_id"]:
                activity = GarminActivity(
                    user_id=user_id,
                    **activity_data
                )
                db.add(activity)
                activity_count += 1
        
        # Sync health metrics for the specified period
        health_metrics_count = 0
        logger.info("Starting health metrics sync", user_id=user_id)
        
        for i in range(min(days, 30)):  # Limit health metrics to 30 days max
            target_date = (datetime.now() - timedelta(days=i)).date()
            
            # Heart rate data
            hr_data = await client.get_heart_rate_data(target_date)
            if hr_data:
                normalized_hr = GarminDataNormalizer.normalize_heart_rate_data(hr_data, target_date)
                
                # Check if metric already exists
                result = await db.execute(
                    select(GarminHealthMetric).where(
                        GarminHealthMetric.user_id == user_id,
                        GarminHealthMetric.metric_type == "heart_rate",
                        GarminHealthMetric.recorded_date == normalized_hr["recorded_date"]
                    )
                )
                existing = result.scalar_one_or_none()
                
                if not existing:
                    metric = GarminHealthMetric(
                        user_id=user_id,
                        **normalized_hr
                    )
                    db.add(metric)
                    health_metrics_count += 1
            
            # Sleep data
            sleep_data = await client.get_sleep_data(target_date)
            if sleep_data:
                normalized_sleep = GarminDataNormalizer.normalize_sleep_data(sleep_data, target_date)
                
                # Check if metric already exists
                result = await db.execute(
                    select(GarminHealthMetric).where(
                        GarminHealthMetric.user_id == user_id,
                        GarminHealthMetric.metric_type == "sleep",
                        GarminHealthMetric.recorded_date == normalized_sleep["recorded_date"]
                    )
                )
                existing = result.scalar_one_or_none()
                
                if not existing:
                    metric = GarminHealthMetric(
                        user_id=user_id,
                        **normalized_sleep
                    )
                    db.add(metric)
                    health_metrics_count += 1
            
            # Body composition data
            body_data = await client.get_body_composition(target_date)
            if body_data:
                normalized_body = GarminDataNormalizer.normalize_body_composition(body_data, target_date)
                
                # Check if metric already exists
                result = await db.execute(
                    select(GarminHealthMetric).where(
                        GarminHealthMetric.user_id == user_id,
                        GarminHealthMetric.metric_type == "body_composition",
                        GarminHealthMetric.recorded_date == normalized_body["recorded_date"]
                    )
                )
                existing = result.scalar_one_or_none()
                
                if not existing:
                    metric = GarminHealthMetric(
                        user_id=user_id,
                        **normalized_body
                    )
                    db.add(metric)
                    health_metrics_count += 1
            
            # Stress data
            stress_data = await client.get_stress_data(target_date)
            if stress_data:
                normalized_stress = GarminDataNormalizer.normalize_stress_data(stress_data, target_date)
                
                # Check if metric already exists
                result = await db.execute(
                    select(GarminHealthMetric).where(
                        GarminHealthMetric.user_id == user_id,
                        GarminHealthMetric.metric_type == "stress",
                        GarminHealthMetric.recorded_date == normalized_stress["recorded_date"]
                    )
                )
                existing = result.scalar_one_or_none()
                
                if not existing:
                    metric = GarminHealthMetric(
                        user_id=user_id,
                        **normalized_stress
                    )
                    db.add(metric)
                    health_metrics_count += 1
        
        await db.commit()
        
        logger.info("Garmin sync completed successfully", 
                   user_id=user_id,
                   activities_synced=activity_count,
                   health_metrics_synced=health_metrics_count)
        
        return SyncResponse(
            message="Garmin data sync completed",
            activities_synced=activity_count,
            health_metrics_synced=health_metrics_count,
            sync_period_days=days,
            user_id=user_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error("Garmin sync failed", error=str(e), user_id=user_id)
        raise HTTPException(status_code=500, detail=f"Sync failed: {str(e)}")

@router.get("/activities", response_model=Dict[str, Any])
async def get_activities(
    user_id: str = Query(..., description="User ID"),
    days: int = Query(30, description="Number of days to retrieve", ge=1, le=365),
    activity_type: Optional[str] = Query(None, description="Filter by activity type"),
    limit: int = Query(100, description="Maximum number of activities", ge=1, le=500),
    db: AsyncSession = Depends(get_db)
):
    """Get user's Garmin activities"""
    try:
        start_date = datetime.now() - timedelta(days=days)
        
        # Build query
        query = select(GarminActivity).where(
            GarminActivity.user_id == user_id,
            GarminActivity.start_time >= start_date
        )
        
        if activity_type:
            query = query.where(GarminActivity.activity_type == activity_type.lower())
        
        query = query.order_by(GarminActivity.start_time.desc()).limit(limit)
        
        # Execute query
        result = await db.execute(query)
        activities = result.scalars().all()
        
        activities_data = []
        for activity in activities:
            activities_data.append({
                "id": str(activity.id),
                "activity_id": activity.activity_id,
                "name": activity.activity_name or "",
                "type": activity.activity_type,
                "start_time": activity.start_time.isoformat() if activity.start_time else None,
                "duration_seconds": activity.duration_seconds,
                "distance_meters": float(activity.distance_meters) if activity.distance_meters else None,
                "calories": activity.calories,
                "avg_heart_rate": activity.avg_heart_rate,
                "max_heart_rate": activity.max_heart_rate
            })
        
        return {
            "activities": activities_data,
            "count": len(activities_data),
            "period_days": days,
            "activity_type_filter": activity_type,
            "user_id": user_id
        }
        
    except Exception as e:
        logger.error("Failed to get activities", error=str(e), user_id=user_id)
        raise HTTPException(status_code=500, detail=f"Failed to get activities: {str(e)}")

@router.get("/health/{metric_type}", response_model=Dict[str, Any])
async def get_health_metrics(
    metric_type: str,
    user_id: str = Query(..., description="User ID"),
    days: int = Query(7, description="Number of days to retrieve", ge=1, le=90),
    db: AsyncSession = Depends(get_db)
):
    """Get user's health metrics"""
    try:
        # Validate metric type
        valid_metrics = ['heart_rate', 'sleep', 'body_composition', 'stress']
        if metric_type not in valid_metrics:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid metric type. Must be one of: {', '.join(valid_metrics)}"
            )
        
        start_date = datetime.now() - timedelta(days=days)
        
        result = await db.execute(
            select(GarminHealthMetric)
            .where(GarminHealthMetric.user_id == user_id)
            .where(GarminHealthMetric.metric_type == metric_type)
            .where(GarminHealthMetric.recorded_date >= start_date)
            .order_by(GarminHealthMetric.recorded_date.desc())
        )
        metrics = result.scalars().all()
        
        metrics_data = []
        for metric in metrics:
            metrics_data.append({
                "id": str(metric.id),
                "metric_type": metric.metric_type,
                "recorded_date": metric.recorded_date.isoformat(),
                "data": metric.metric_data,
                "processed_at": metric.processed_at.isoformat()
            })
        
        return {
            "metrics": metrics_data,
            "count": len(metrics_data),
            "metric_type": metric_type,
            "period_days": days,
            "user_id": user_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get health metrics", 
                    error=str(e), user_id=user_id, metric_type=metric_type)
        raise HTTPException(status_code=500, detail=f"Failed to get health metrics: {str(e)}")

@router.get("/health/summary")
async def get_health_summary(
    user_id: str = Query(..., description="User ID"),
    days: int = Query(7, description="Number of days for summary", ge=1, le=30),
    db: AsyncSession = Depends(get_db)
):
    """Get a summary of all health metrics for a user"""
    try:
        start_date = datetime.now() - timedelta(days=days)
        
        result = await db.execute(
            select(GarminHealthMetric)
            .where(GarminHealthMetric.user_id == user_id)
            .where(GarminHealthMetric.recorded_date >= start_date)
            .order_by(GarminHealthMetric.recorded_date.desc(), GarminHealthMetric.metric_type)
        )
        metrics = result.scalars().all()
        
        # Group metrics by type
        summary = {}
        for metric in metrics:
            metric_type = metric.metric_type
            if metric_type not in summary:
                summary[metric_type] = {
                    "count": 0,
                    "latest": None,
                    "data_points": []
                }
            
            summary[metric_type]["count"] += 1
            
            metric_data = {
                "recorded_date": metric.recorded_date.isoformat(),
                "data": metric.metric_data
            }
            
            if summary[metric_type]["latest"] is None:
                summary[metric_type]["latest"] = metric_data
            
            summary[metric_type]["data_points"].append(metric_data)
        
        return {
            "summary": summary,
            "period_days": days,
            "user_id": user_id,
            "total_metrics": len(metrics)
        }
        
    except Exception as e:
        logger.error("Failed to get health summary", error=str(e), user_id=user_id)
        raise HTTPException(status_code=500, detail=f"Failed to get health summary: {str(e)}")

@router.get("/sync/status")
async def get_sync_status(
    user_id: str = Query(..., description="User ID"),
    db: AsyncSession = Depends(get_db)
):
    """Get sync status and statistics for a user"""
    try:
        # Check if user has credentials
        credentials_exist = await credential_service.get_credentials(db, user_id) is not None
        
        # Get latest activity
        activity_result = await db.execute(
            select(GarminActivity)
            .where(GarminActivity.user_id == user_id)
            .order_by(GarminActivity.processed_at.desc())
            .limit(1)
        )
        latest_activity = activity_result.scalar_one_or_none()
        
        # Get latest health metric
        health_result = await db.execute(
            select(GarminHealthMetric)
            .where(GarminHealthMetric.user_id == user_id)
            .order_by(GarminHealthMetric.processed_at.desc())
            .limit(1)
        )
        latest_health_metric = health_result.scalar_one_or_none()
        
        # Count total data
        activity_count_result = await db.execute(
            select(GarminActivity).where(GarminActivity.user_id == user_id)
        )
        total_activities = len(activity_count_result.scalars().all())
        
        health_count_result = await db.execute(
            select(GarminHealthMetric).where(GarminHealthMetric.user_id == user_id)
        )
        total_health_metrics = len(health_count_result.scalars().all())
        
        return {
            "user_id": user_id,
            "credentials_configured": credentials_exist,
            "total_activities": total_activities,
            "total_health_metrics": total_health_metrics,
            "latest_activity_sync": latest_activity.processed_at.isoformat() if latest_activity else None,
            "latest_health_sync": latest_health_metric.processed_at.isoformat() if latest_health_metric else None,
            "sync_ready": credentials_exist
        }
        
    except Exception as e:
        logger.error("Failed to get sync status", error=str(e), user_id=user_id)
        raise HTTPException(status_code=500, detail=f"Failed to get sync status: {str(e)}")