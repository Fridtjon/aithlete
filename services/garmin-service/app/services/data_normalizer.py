"""
Data normalization service for converting raw Garmin data to standardized format
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, date, timezone
import structlog
from decimal import Decimal

logger = structlog.get_logger(__name__)

class GarminDataNormalizer:
    """Normalize raw Garmin data into consistent, database-ready format"""
    
    @staticmethod
    def normalize_activity(raw_activity: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize a single activity from Garmin Connect"""
        try:
            # Extract basic activity information
            activity_id = str(raw_activity.get('activityId', ''))
            
            # Parse start time
            start_time_str = raw_activity.get('startTimeLocal', '')
            start_time = None
            if start_time_str:
                try:
                    start_time = datetime.fromisoformat(start_time_str.replace('Z', '+00:00'))
                except ValueError:
                    logger.warning("Invalid start time format", 
                                 activity_id=activity_id, start_time=start_time_str)
            
            # Normalize activity type
            activity_type = None
            if 'activityType' in raw_activity and raw_activity['activityType']:
                activity_type = raw_activity['activityType'].get('typeKey', '').lower()
            
            # Extract metrics with safe conversion
            duration = raw_activity.get('duration')
            if duration and isinstance(duration, (int, float)):
                duration = int(duration)
            
            distance = raw_activity.get('distance')
            if distance and isinstance(distance, (int, float)):
                distance = Decimal(str(distance))
            
            calories = raw_activity.get('calories')
            if calories and isinstance(calories, (int, float)):
                calories = int(calories)
            
            # Heart rate data
            avg_hr = raw_activity.get('averageHR')
            max_hr = raw_activity.get('maxHR')
            
            normalized = {
                'activity_id': activity_id,
                'activity_name': raw_activity.get('activityName', ''),
                'activity_type': activity_type,
                'start_time': start_time,
                'duration_seconds': duration,
                'distance_meters': distance,
                'calories': calories,
                'avg_heart_rate': int(avg_hr) if avg_hr and isinstance(avg_hr, (int, float)) else None,
                'max_heart_rate': int(max_hr) if max_hr and isinstance(max_hr, (int, float)) else None,
                'raw_data': raw_activity  # Store complete raw data for future reference
            }
            
            logger.debug("Normalized activity", 
                        activity_id=activity_id, 
                        activity_type=activity_type,
                        duration=duration)
            
            return normalized
            
        except Exception as e:
            logger.error("Failed to normalize activity", 
                        error=str(e), 
                        activity_id=raw_activity.get('activityId', 'unknown'))
            raise
    
    @staticmethod
    def normalize_heart_rate_data(raw_hr_data: Dict[str, Any], target_date: date) -> Dict[str, Any]:
        """Normalize heart rate data for a specific date"""
        try:
            # Extract key metrics from heart rate data
            normalized_data = {}
            
            # Resting heart rate
            if 'restingHeartRate' in raw_hr_data:
                normalized_data['resting_heart_rate'] = raw_hr_data['restingHeartRate']
            
            # Heart rate zones
            if 'heartRateZones' in raw_hr_data:
                normalized_data['hr_zones'] = raw_hr_data['heartRateZones']
            
            # Time in zones
            if 'timeInZones' in raw_hr_data:
                normalized_data['time_in_zones'] = raw_hr_data['timeInZones']
            
            # Heart rate variability
            if 'hrv' in raw_hr_data:
                normalized_data['hrv'] = raw_hr_data['hrv']
            
            # Max and average heart rate for the day
            if 'maxHeartRate' in raw_hr_data:
                normalized_data['max_heart_rate'] = raw_hr_data['maxHeartRate']
            
            if 'averageHeartRate' in raw_hr_data:
                normalized_data['avg_heart_rate'] = raw_hr_data['averageHeartRate']
            
            # Heart rate samples throughout the day
            if 'heartRateValues' in raw_hr_data:
                normalized_data['hr_samples'] = raw_hr_data['heartRateValues']
            
            return {
                'metric_type': 'heart_rate',
                'recorded_date': datetime.combine(target_date, datetime.min.time()).replace(tzinfo=timezone.utc),
                'metric_data': normalized_data
            }
            
        except Exception as e:
            logger.error("Failed to normalize heart rate data", 
                        error=str(e), date=target_date.isoformat())
            raise
    
    @staticmethod
    def normalize_sleep_data(raw_sleep_data: Dict[str, Any], target_date: date) -> Dict[str, Any]:
        """Normalize sleep data for a specific date"""
        try:
            normalized_data = {}
            
            # Sleep duration and efficiency
            if 'sleepTimeSeconds' in raw_sleep_data:
                normalized_data['sleep_duration_seconds'] = raw_sleep_data['sleepTimeSeconds']
            
            if 'sleepEfficiency' in raw_sleep_data:
                normalized_data['sleep_efficiency'] = raw_sleep_data['sleepEfficiency']
            
            # Sleep stages
            if 'sleepLevels' in raw_sleep_data:
                sleep_stages = {}
                for level in raw_sleep_data['sleepLevels']:
                    stage = level.get('level', '').lower()
                    if stage in ['deep', 'light', 'rem', 'awake']:
                        sleep_stages[f"{stage}_seconds"] = level.get('seconds', 0)
                normalized_data['sleep_stages'] = sleep_stages
            
            # Sleep times
            if 'sleepStartTimestampLocal' in raw_sleep_data:
                try:
                    sleep_start = datetime.fromisoformat(
                        raw_sleep_data['sleepStartTimestampLocal'].replace('Z', '+00:00')
                    )
                    normalized_data['sleep_start'] = sleep_start
                except ValueError:
                    pass
            
            if 'sleepEndTimestampLocal' in raw_sleep_data:
                try:
                    sleep_end = datetime.fromisoformat(
                        raw_sleep_data['sleepEndTimestampLocal'].replace('Z', '+00:00')
                    )
                    normalized_data['sleep_end'] = sleep_end
                except ValueError:
                    pass
            
            # Sleep score (if available)
            if 'sleepScore' in raw_sleep_data:
                normalized_data['sleep_score'] = raw_sleep_data['sleepScore']
            
            # Restlessness
            if 'restlessness' in raw_sleep_data:
                normalized_data['restlessness'] = raw_sleep_data['restlessness']
            
            return {
                'metric_type': 'sleep',
                'recorded_date': datetime.combine(target_date, datetime.min.time()).replace(tzinfo=timezone.utc),
                'metric_data': normalized_data
            }
            
        except Exception as e:
            logger.error("Failed to normalize sleep data", 
                        error=str(e), date=target_date.isoformat())
            raise
    
    @staticmethod
    def normalize_body_composition(raw_body_data: Dict[str, Any], target_date: date) -> Dict[str, Any]:
        """Normalize body composition data"""
        try:
            normalized_data = {}
            
            # Weight
            if 'weight' in raw_body_data:
                normalized_data['weight_kg'] = raw_body_data['weight']
            
            # Body fat percentage
            if 'bodyFat' in raw_body_data:
                normalized_data['body_fat_percentage'] = raw_body_data['bodyFat']
            
            # Muscle mass
            if 'muscleMass' in raw_body_data:
                normalized_data['muscle_mass_kg'] = raw_body_data['muscleMass']
            
            # BMI
            if 'bmi' in raw_body_data:
                normalized_data['bmi'] = raw_body_data['bmi']
            
            # Body water
            if 'bodyWater' in raw_body_data:
                normalized_data['body_water_percentage'] = raw_body_data['bodyWater']
            
            # Bone mass
            if 'boneMass' in raw_body_data:
                normalized_data['bone_mass_kg'] = raw_body_data['boneMass']
            
            return {
                'metric_type': 'body_composition',
                'recorded_date': datetime.combine(target_date, datetime.min.time()).replace(tzinfo=timezone.utc),
                'metric_data': normalized_data
            }
            
        except Exception as e:
            logger.error("Failed to normalize body composition data", 
                        error=str(e), date=target_date.isoformat())
            raise
    
    @staticmethod
    def normalize_stress_data(raw_stress_data: Dict[str, Any], target_date: date) -> Dict[str, Any]:
        """Normalize stress data"""
        try:
            normalized_data = {}
            
            # Average stress level
            if 'averageStressLevel' in raw_stress_data:
                normalized_data['avg_stress_level'] = raw_stress_data['averageStressLevel']
            
            # Max stress level
            if 'maxStressLevel' in raw_stress_data:
                normalized_data['max_stress_level'] = raw_stress_data['maxStressLevel']
            
            # Stress duration
            if 'stressDuration' in raw_stress_data:
                normalized_data['stress_duration_seconds'] = raw_stress_data['stressDuration']
            
            # Rest periods
            if 'restStressDuration' in raw_stress_data:
                normalized_data['rest_duration_seconds'] = raw_stress_data['restStressDuration']
            
            # Activity stress
            if 'activityStressDuration' in raw_stress_data:
                normalized_data['activity_stress_duration_seconds'] = raw_stress_data['activityStressDuration']
            
            # Low stress duration
            if 'lowStressDuration' in raw_stress_data:
                normalized_data['low_stress_duration_seconds'] = raw_stress_data['lowStressDuration']
            
            # Medium stress duration
            if 'mediumStressDuration' in raw_stress_data:
                normalized_data['medium_stress_duration_seconds'] = raw_stress_data['mediumStressDuration']
            
            # High stress duration
            if 'highStressDuration' in raw_stress_data:
                normalized_data['high_stress_duration_seconds'] = raw_stress_data['highStressDuration']
            
            # Stress level samples throughout the day
            if 'stressLevelValues' in raw_stress_data:
                normalized_data['stress_samples'] = raw_stress_data['stressLevelValues']
            
            return {
                'metric_type': 'stress',
                'recorded_date': datetime.combine(target_date, datetime.min.time()).replace(tzinfo=timezone.utc),
                'metric_data': normalized_data
            }
            
        except Exception as e:
            logger.error("Failed to normalize stress data", 
                        error=str(e), date=target_date.isoformat())
            raise
    
    @staticmethod
    def normalize_activities_batch(raw_activities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Normalize a batch of activities"""
        normalized_activities = []
        
        for raw_activity in raw_activities:
            try:
                normalized = GarminDataNormalizer.normalize_activity(raw_activity)
                if normalized['activity_id']:  # Only add if we have a valid activity ID
                    normalized_activities.append(normalized)
            except Exception as e:
                logger.warning("Skipping activity normalization", 
                             error=str(e),
                             activity_id=raw_activity.get('activityId', 'unknown'))
                continue
        
        logger.info(f"Normalized {len(normalized_activities)}/{len(raw_activities)} activities")
        return normalized_activities