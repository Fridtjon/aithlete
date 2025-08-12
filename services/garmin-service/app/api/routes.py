from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timedelta
from typing import List, Optional
import structlog

from app.core.database import get_db
from app.services.garmin_client import garmin_client
from app.models.garmin import GarminActivity, GarminHealthMetric

logger = structlog.get_logger(__name__)
router = APIRouter()

@router.post("/sync")
async def sync_garmin_data(
    user_id: str = Query(..., description="User ID to sync data for"),
    days: int = Query(30, description="Number of days to sync"),
    db: AsyncSession = Depends(get_db)
):
    """Sync Garmin data for a user"""
    try:
        # For now, we'll use hardcoded credentials
        # In production, these would be fetched from encrypted storage
        username = "test_user"  # This would be retrieved from user_credentials table
        password = "test_pass"  # This would be decrypted from user_credentials table
        
        if not await garmin_client.authenticate(username, password):
            raise HTTPException(status_code=401, detail="Failed to authenticate with Garmin Connect")
        
        start_date = datetime.now() - timedelta(days=days)
        
        # Sync activities
        activities = await garmin_client.get_activities(start_date)
        activity_count = 0
        
        for activity_data in activities:
            # Check if activity already exists
            existing = await db.get(GarminActivity, {"user_id": user_id, "activity_id": activity_data.get("activityId")})
            
            if not existing:
                activity = GarminActivity(
                    user_id=user_id,
                    activity_id=str(activity_data.get("activityId")),
                    activity_type=activity_data.get("activityType", {}).get("typeKey"),
                    activity_name=activity_data.get("activityName"),
                    start_time=datetime.fromisoformat(activity_data["startTimeLocal"].replace('Z', '+00:00')),
                    duration_seconds=activity_data.get("duration"),
                    distance_meters=activity_data.get("distance"),
                    calories=activity_data.get("calories"),
                    avg_heart_rate=activity_data.get("averageHR"),
                    max_heart_rate=activity_data.get("maxHR"),
                    raw_data=activity_data
                )
                db.add(activity)
                activity_count += 1
        
        # Sync health metrics for the past week
        health_metrics_count = 0
        for i in range(7):
            date = datetime.now() - timedelta(days=i)
            
            # Heart rate data
            try:
                hr_data = await garmin_client.get_heart_rate_data(date)
                if hr_data:
                    metric = GarminHealthMetric(
                        user_id=user_id,
                        metric_type="heart_rate",
                        recorded_date=date,
                        metric_data=hr_data
                    )
                    db.add(metric)
                    health_metrics_count += 1
            except Exception as e:
                logger.warning(f"Failed to get heart rate data for {date.strftime('%Y-%m-%d')}: {e}")
            
            # Sleep data
            try:
                sleep_data = await garmin_client.get_sleep_data(date)
                if sleep_data:
                    metric = GarminHealthMetric(
                        user_id=user_id,
                        metric_type="sleep",
                        recorded_date=date,
                        metric_data=sleep_data
                    )
                    db.add(metric)
                    health_metrics_count += 1
            except Exception as e:
                logger.warning(f"Failed to get sleep data for {date.strftime('%Y-%m-%d')}: {e}")
        
        await db.commit()
        
        return {
            "message": "Garmin data sync completed",
            "activities_synced": activity_count,
            "health_metrics_synced": health_metrics_count,
            "sync_period_days": days
        }
        
    except Exception as e:
        logger.error("Garmin sync failed", error=str(e), user_id=user_id)
        raise HTTPException(status_code=500, detail=f"Sync failed: {str(e)}")

@router.get("/activities")
async def get_activities(
    user_id: str = Query(..., description="User ID"),
    days: int = Query(30, description="Number of days to retrieve"),
    db: AsyncSession = Depends(get_db)
):
    """Get user's Garmin activities"""
    try:
        start_date = datetime.now() - timedelta(days=days)
        
        # Query activities from database
        result = await db.execute(
            select(GarminActivity)
            .where(GarminActivity.user_id == user_id)
            .where(GarminActivity.start_time >= start_date)
            .order_by(GarminActivity.start_time.desc())
        )
        activities = result.scalars().all()
        
        return {
            "activities": [
                {
                    "id": str(activity.id),
                    "activity_id": activity.activity_id,
                    "name": activity.activity_name,
                    "type": activity.activity_type,
                    "start_time": activity.start_time.isoformat(),
                    "duration_seconds": activity.duration_seconds,
                    "distance_meters": float(activity.distance_meters) if activity.distance_meters else None,
                    "calories": activity.calories,
                    "avg_heart_rate": activity.avg_heart_rate,
                    "max_heart_rate": activity.max_heart_rate
                }
                for activity in activities
            ],
            "count": len(activities),
            "period_days": days
        }
        
    except Exception as e:
        logger.error("Failed to get activities", error=str(e), user_id=user_id)
        raise HTTPException(status_code=500, detail=f"Failed to get activities: {str(e)}")

@router.get("/health/{metric_type}")
async def get_health_metrics(
    metric_type: str,
    user_id: str = Query(..., description="User ID"),
    days: int = Query(7, description="Number of days to retrieve"),
    db: AsyncSession = Depends(get_db)
):
    """Get user's health metrics"""
    try:
        start_date = datetime.now() - timedelta(days=days)
        
        result = await db.execute(
            select(GarminHealthMetric)
            .where(GarminHealthMetric.user_id == user_id)
            .where(GarminHealthMetric.metric_type == metric_type)
            .where(GarminHealthMetric.recorded_date >= start_date)
            .order_by(GarminHealthMetric.recorded_date.desc())
        )
        metrics = result.scalars().all()
        
        return {
            "metrics": [
                {
                    "id": str(metric.id),
                    "metric_type": metric.metric_type,
                    "recorded_date": metric.recorded_date.isoformat(),
                    "data": metric.metric_data,
                    "processed_at": metric.processed_at.isoformat()
                }
                for metric in metrics
            ],
            "count": len(metrics),
            "metric_type": metric_type,
            "period_days": days
        }
        
    except Exception as e:
        logger.error("Failed to get health metrics", error=str(e), user_id=user_id, metric_type=metric_type)
        raise HTTPException(status_code=500, detail=f"Failed to get health metrics: {str(e)}")