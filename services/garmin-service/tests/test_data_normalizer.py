"""
Unit tests for Garmin data normalizer
"""

import pytest
from datetime import datetime, date, timezone
from decimal import Decimal
from app.services.data_normalizer import GarminDataNormalizer


class TestActivityNormalization:
    """Test activity data normalization"""
    
    def test_normalize_complete_activity(self):
        """Test normalizing a complete activity with all fields"""
        raw_activity = {
            'activityId': 12345,
            'activityName': 'Morning Run',
            'activityType': {'typeKey': 'RUNNING'},
            'startTimeLocal': '2024-01-15T07:30:00',
            'duration': 3600,
            'distance': 10000.5,
            'calories': 450,
            'averageHR': 145,
            'maxHR': 170,
            'additionalData': 'should be preserved'
        }
        
        normalized = GarminDataNormalizer.normalize_activity(raw_activity)
        
        assert normalized['activity_id'] == '12345'
        assert normalized['activity_name'] == 'Morning Run'
        assert normalized['activity_type'] == 'running'
        assert normalized['start_time'] == datetime.fromisoformat('2024-01-15T07:30:00')
        assert normalized['duration_seconds'] == 3600
        assert normalized['distance_meters'] == Decimal('10000.5')
        assert normalized['calories'] == 450
        assert normalized['avg_heart_rate'] == 145
        assert normalized['max_heart_rate'] == 170
        assert normalized['raw_data'] == raw_activity
    
    def test_normalize_minimal_activity(self):
        """Test normalizing activity with minimal fields"""
        raw_activity = {
            'activityId': 67890,
            'activityName': 'Quick Walk'
        }
        
        normalized = GarminDataNormalizer.normalize_activity(raw_activity)
        
        assert normalized['activity_id'] == '67890'
        assert normalized['activity_name'] == 'Quick Walk'
        assert normalized['activity_type'] is None
        assert normalized['start_time'] is None
        assert normalized['duration_seconds'] is None
        assert normalized['distance_meters'] is None
        assert normalized['calories'] is None
        assert normalized['avg_heart_rate'] is None
        assert normalized['max_heart_rate'] is None
        assert normalized['raw_data'] == raw_activity
    
    def test_normalize_activity_with_iso_timestamp(self):
        """Test normalizing activity with ISO timestamp including Z"""
        raw_activity = {
            'activityId': 11111,
            'startTimeLocal': '2024-01-15T07:30:00Z'
        }
        
        normalized = GarminDataNormalizer.normalize_activity(raw_activity)
        
        assert normalized['start_time'] == datetime.fromisoformat('2024-01-15T07:30:00+00:00')
    
    def test_normalize_activity_invalid_timestamp(self):
        """Test normalizing activity with invalid timestamp"""
        raw_activity = {
            'activityId': 22222,
            'startTimeLocal': 'invalid-timestamp'
        }
        
        normalized = GarminDataNormalizer.normalize_activity(raw_activity)
        
        assert normalized['start_time'] is None
    
    def test_normalize_activity_type_conversion(self):
        """Test activity type conversion to lowercase"""
        raw_activity = {
            'activityId': 33333,
            'activityType': {'typeKey': 'STRENGTH_TRAINING'}
        }
        
        normalized = GarminDataNormalizer.normalize_activity(raw_activity)
        
        assert normalized['activity_type'] == 'strength_training'
    
    def test_normalize_activity_numeric_conversions(self):
        """Test proper numeric type conversions"""
        raw_activity = {
            'activityId': 44444,
            'duration': 3600.5,  # Float duration should become int
            'distance': 5000.0,   # Float distance should become Decimal
            'calories': 250.8,    # Float calories should become int
            'averageHR': 140.5,   # Float HR should become int
            'maxHR': '165'        # String HR should be handled
        }
        
        normalized = GarminDataNormalizer.normalize_activity(raw_activity)
        
        assert normalized['duration_seconds'] == 3600
        assert normalized['distance_meters'] == Decimal('5000.0')
        assert normalized['calories'] == 250
        assert normalized['avg_heart_rate'] == 140
        # String HR should be None (not int/float)
        assert normalized['max_heart_rate'] is None


class TestHeartRateNormalization:
    """Test heart rate data normalization"""
    
    def test_normalize_complete_heart_rate_data(self):
        """Test normalizing complete heart rate data"""
        target_date = date(2024, 1, 15)
        raw_hr_data = {
            'restingHeartRate': 65,
            'heartRateZones': [
                {'zone': 1, 'min': 65, 'max': 120},
                {'zone': 2, 'min': 120, 'max': 150}
            ],
            'timeInZones': [
                {'zone': 1, 'timeSeconds': 3600},
                {'zone': 2, 'timeSeconds': 1800}
            ],
            'hrv': 45,
            'maxHeartRate': 180,
            'averageHeartRate': 125,
            'heartRateValues': [70, 72, 75, 80]
        }
        
        normalized = GarminDataNormalizer.normalize_heart_rate_data(raw_hr_data, target_date)
        
        assert normalized['metric_type'] == 'heart_rate'
        assert normalized['recorded_date'] == datetime.combine(target_date, datetime.min.time()).replace(tzinfo=timezone.utc)
        
        data = normalized['metric_data']
        assert data['resting_heart_rate'] == 65
        assert len(data['hr_zones']) == 2
        assert data['time_in_zones'] == raw_hr_data['timeInZones']
        assert data['hrv'] == 45
        assert data['max_heart_rate'] == 180
        assert data['avg_heart_rate'] == 125
        assert data['hr_samples'] == [70, 72, 75, 80]
    
    def test_normalize_minimal_heart_rate_data(self):
        """Test normalizing minimal heart rate data"""
        target_date = date(2024, 1, 15)
        raw_hr_data = {
            'restingHeartRate': 70
        }
        
        normalized = GarminDataNormalizer.normalize_heart_rate_data(raw_hr_data, target_date)
        
        assert normalized['metric_type'] == 'heart_rate'
        data = normalized['metric_data']
        assert data['resting_heart_rate'] == 70
        assert 'hr_zones' not in data
        assert 'hrv' not in data


class TestSleepNormalization:
    """Test sleep data normalization"""
    
    def test_normalize_complete_sleep_data(self):
        """Test normalizing complete sleep data"""
        target_date = date(2024, 1, 15)
        raw_sleep_data = {
            'sleepTimeSeconds': 28800,  # 8 hours
            'sleepEfficiency': 85,
            'sleepLevels': [
                {'level': 'deep', 'seconds': 7200},
                {'level': 'light', 'seconds': 18000},
                {'level': 'rem', 'seconds': 3600}
            ],
            'sleepStartTimestampLocal': '2024-01-14T23:00:00',
            'sleepEndTimestampLocal': '2024-01-15T07:00:00Z',
            'sleepScore': 82,
            'restlessness': 15
        }
        
        normalized = GarminDataNormalizer.normalize_sleep_data(raw_sleep_data, target_date)
        
        assert normalized['metric_type'] == 'sleep'
        assert normalized['recorded_date'] == datetime.combine(target_date, datetime.min.time()).replace(tzinfo=timezone.utc)
        
        data = normalized['metric_data']
        assert data['sleep_duration_seconds'] == 28800
        assert data['sleep_efficiency'] == 85
        assert data['sleep_stages']['deep_seconds'] == 7200
        assert data['sleep_stages']['light_seconds'] == 18000
        assert data['sleep_stages']['rem_seconds'] == 3600
        assert data['sleep_start'] == datetime.fromisoformat('2024-01-14T23:00:00')
        assert data['sleep_end'] == datetime.fromisoformat('2024-01-15T07:00:00+00:00')
        assert data['sleep_score'] == 82
        assert data['restlessness'] == 15
    
    def test_normalize_sleep_data_with_invalid_timestamps(self):
        """Test sleep data with invalid timestamps"""
        target_date = date(2024, 1, 15)
        raw_sleep_data = {
            'sleepTimeSeconds': 28800,
            'sleepStartTimestampLocal': 'invalid-timestamp',
            'sleepEndTimestampLocal': 'also-invalid'
        }
        
        normalized = GarminDataNormalizer.normalize_sleep_data(raw_sleep_data, target_date)
        
        data = normalized['metric_data']
        assert data['sleep_duration_seconds'] == 28800
        assert 'sleep_start' not in data
        assert 'sleep_end' not in data
    
    def test_normalize_sleep_levels_filtering(self):
        """Test that only valid sleep levels are included"""
        target_date = date(2024, 1, 15)
        raw_sleep_data = {
            'sleepLevels': [
                {'level': 'deep', 'seconds': 7200},
                {'level': 'invalid_level', 'seconds': 1800},  # Should be filtered out
                {'level': 'REM', 'seconds': 3600},  # Should be converted to lowercase
                {'level': 'awake', 'seconds': 600}
            ]
        }
        
        normalized = GarminDataNormalizer.normalize_sleep_data(raw_sleep_data, target_date)
        
        stages = normalized['metric_data']['sleep_stages']
        assert 'deep_seconds' in stages
        assert 'rem_seconds' in stages  # REM should be converted to lowercase
        assert 'awake_seconds' in stages
        assert 'invalid_level_seconds' not in stages


class TestBodyCompositionNormalization:
    """Test body composition data normalization"""
    
    def test_normalize_complete_body_composition(self):
        """Test normalizing complete body composition data"""
        target_date = date(2024, 1, 15)
        raw_body_data = {
            'weight': 75.5,
            'bodyFat': 18.2,
            'muscleMass': 35.8,
            'bmi': 23.4,
            'bodyWater': 60.5,
            'boneMass': 3.2
        }
        
        normalized = GarminDataNormalizer.normalize_body_composition(raw_body_data, target_date)
        
        assert normalized['metric_type'] == 'body_composition'
        assert normalized['recorded_date'] == datetime.combine(target_date, datetime.min.time()).replace(tzinfo=timezone.utc)
        
        data = normalized['metric_data']
        assert data['weight_kg'] == 75.5
        assert data['body_fat_percentage'] == 18.2
        assert data['muscle_mass_kg'] == 35.8
        assert data['bmi'] == 23.4
        assert data['body_water_percentage'] == 60.5
        assert data['bone_mass_kg'] == 3.2


class TestStressNormalization:
    """Test stress data normalization"""
    
    def test_normalize_complete_stress_data(self):
        """Test normalizing complete stress data"""
        target_date = date(2024, 1, 15)
        raw_stress_data = {
            'averageStressLevel': 25,
            'maxStressLevel': 65,
            'stressDuration': 14400,  # 4 hours
            'restStressDuration': 28800,  # 8 hours
            'activityStressDuration': 3600,  # 1 hour
            'lowStressDuration': 21600,  # 6 hours
            'mediumStressDuration': 7200,  # 2 hours
            'highStressDuration': 1800,   # 30 minutes
            'stressLevelValues': [20, 25, 30, 45, 35, 15]
        }
        
        normalized = GarminDataNormalizer.normalize_stress_data(raw_stress_data, target_date)
        
        assert normalized['metric_type'] == 'stress'
        assert normalized['recorded_date'] == datetime.combine(target_date, datetime.min.time()).replace(tzinfo=timezone.utc)
        
        data = normalized['metric_data']
        assert data['avg_stress_level'] == 25
        assert data['max_stress_level'] == 65
        assert data['stress_duration_seconds'] == 14400
        assert data['rest_duration_seconds'] == 28800
        assert data['activity_stress_duration_seconds'] == 3600
        assert data['low_stress_duration_seconds'] == 21600
        assert data['medium_stress_duration_seconds'] == 7200
        assert data['high_stress_duration_seconds'] == 1800
        assert data['stress_samples'] == [20, 25, 30, 45, 35, 15]


class TestBatchNormalization:
    """Test batch activity normalization"""
    
    def test_normalize_activities_batch_success(self):
        """Test successful batch normalization"""
        raw_activities = [
            {'activityId': 1, 'activityName': 'Run 1'},
            {'activityId': 2, 'activityName': 'Run 2'},
            {'activityId': 3, 'activityName': 'Run 3'}
        ]
        
        normalized = GarminDataNormalizer.normalize_activities_batch(raw_activities)
        
        assert len(normalized) == 3
        assert all(activity['activity_id'] for activity in normalized)
        assert normalized[0]['activity_name'] == 'Run 1'
        assert normalized[1]['activity_name'] == 'Run 2'
        assert normalized[2]['activity_name'] == 'Run 3'
    
    def test_normalize_activities_batch_with_failures(self):
        """Test batch normalization with some failures"""
        raw_activities = [
            {'activityId': 1, 'activityName': 'Valid Run'},
            {'invalid': 'data'},  # This should fail normalization
            {'activityId': '', 'activityName': 'Empty ID'},  # Empty ID should be filtered
            {'activityId': 3, 'activityName': 'Another Valid Run'}
        ]
        
        normalized = GarminDataNormalizer.normalize_activities_batch(raw_activities)
        
        # Should only include activities with valid activity IDs
        assert len(normalized) == 2
        assert normalized[0]['activity_name'] == 'Valid Run'
        assert normalized[1]['activity_name'] == 'Another Valid Run'
    
    def test_normalize_activities_batch_empty_list(self):
        """Test batch normalization with empty list"""
        normalized = GarminDataNormalizer.normalize_activities_batch([])
        
        assert normalized == []


class TestErrorHandling:
    """Test error handling in data normalization"""
    
    def test_normalize_activity_missing_activity_id(self):
        """Test that missing activity ID results in empty ID"""
        raw_activity = {'activityName': 'Test Activity'}
        
        normalized = GarminDataNormalizer.normalize_activity(raw_activity)
        assert normalized['activity_id'] == ''
    
    def test_normalize_heart_rate_data_error(self):
        """Test error handling in heart rate normalization"""
        target_date = date(2024, 1, 15)
        
        # Create a scenario that would cause an error
        with pytest.raises(Exception):
            GarminDataNormalizer.normalize_heart_rate_data(None, target_date)
    
    def test_normalize_sleep_data_error(self):
        """Test error handling in sleep data normalization"""
        target_date = date(2024, 1, 15)
        
        with pytest.raises(Exception):
            GarminDataNormalizer.normalize_sleep_data(None, target_date)
    
    def test_normalize_body_composition_error(self):
        """Test error handling in body composition normalization"""
        target_date = date(2024, 1, 15)
        
        with pytest.raises(Exception):
            GarminDataNormalizer.normalize_body_composition(None, target_date)
    
    def test_normalize_stress_data_error(self):
        """Test error handling in stress data normalization"""
        target_date = date(2024, 1, 15)
        
        with pytest.raises(Exception):
            GarminDataNormalizer.normalize_stress_data(None, target_date)