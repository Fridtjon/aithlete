-- AIthlete Seed Data
-- Default goal templates and reference data

-- Insert default goal templates
INSERT INTO goal_templates (id, name, category, description, default_parameters, metrics_tracked) VALUES
(
    uuid_generate_v4(),
    'Weight Loss Program',
    'weight_loss',
    'Structured weight loss program focusing on sustainable calorie deficit and cardio exercise',
    '{
        "target_weight_loss_kg": 10,
        "timeline_weeks": 16,
        "calorie_deficit_daily": 500,
        "cardio_sessions_per_week": 4,
        "strength_sessions_per_week": 2,
        "target_rate_kg_per_week": 0.5
    }',
    '["weight", "body_fat_percentage", "daily_calories", "weekly_cardio_minutes", "weekly_strength_sessions"]'
),
(
    uuid_generate_v4(),
    'Muscle Building Program',
    'muscle_gain',
    'Progressive overload strength training program for muscle growth and strength gains',
    '{
        "target_weight_gain_kg": 5,
        "timeline_weeks": 20,
        "calorie_surplus_daily": 300,
        "strength_sessions_per_week": 4,
        "cardio_sessions_per_week": 2,
        "target_rate_kg_per_week": 0.25
    }',
    '["weight", "muscle_mass", "strength_metrics", "weekly_training_volume", "progressive_overload"]'
),
(
    uuid_generate_v4(),
    'Endurance Training',
    'endurance',
    'Cardiovascular endurance training for running, cycling, or general aerobic fitness',
    '{
        "target_distance_km": 42.2,
        "timeline_weeks": 16,
        "weekly_volume_increase_percent": 10,
        "long_runs_per_week": 1,
        "tempo_runs_per_week": 1,
        "easy_runs_per_week": 3
    }',
    '["weekly_distance", "pace_improvements", "vo2_max", "resting_heart_rate", "training_zones"]'
),
(
    uuid_generate_v4(),
    'General Fitness',
    'general_fitness',
    'Balanced fitness program combining strength, cardio, and flexibility for overall health',
    '{
        "activity_days_per_week": 5,
        "strength_sessions_per_week": 2,
        "cardio_sessions_per_week": 3,
        "flexibility_sessions_per_week": 2,
        "target_active_minutes_daily": 60
    }',
    '["weekly_activity_days", "active_minutes", "strength_progression", "cardio_endurance", "flexibility_score"]'
),
(
    uuid_generate_v4(),
    'Athletic Performance',
    'performance',
    'Sport-specific training program focused on performance metrics and competitive goals',
    '{
        "sport": "running",
        "performance_metric": "5k_time",
        "target_improvement_percent": 10,
        "timeline_weeks": 12,
        "periodization": "linear",
        "peak_week": 10
    }',
    '["performance_tests", "training_stress_score", "recovery_metrics", "technique_scores", "competition_results"]'
),
(
    uuid_generate_v4(),
    'Injury Recovery',
    'recovery',
    'Rehabilitation and gradual return to activity program with focus on injury prevention',
    '{
        "injury_type": "knee",
        "recovery_phase": "early",
        "timeline_weeks": 8,
        "pain_threshold": 3,
        "activity_progression": "conservative",
        "pt_sessions_per_week": 2
    }',
    '["pain_levels", "range_of_motion", "strength_deficits", "functional_tests", "activity_tolerance"]'
);

-- Insert sample metric types for reference
CREATE TABLE IF NOT EXISTS metric_definitions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    metric_name VARCHAR(100) UNIQUE NOT NULL,
    category VARCHAR(50) NOT NULL,
    unit VARCHAR(20),
    description TEXT,
    calculation_method TEXT,
    data_sources TEXT[] DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

INSERT INTO metric_definitions (metric_name, category, unit, description, calculation_method, data_sources) VALUES
('daily_steps', 'activity', 'steps', 'Total steps taken per day', 'Sum from activity trackers', ARRAY['garmin']),
('resting_heart_rate', 'health', 'bpm', 'Resting heart rate measurement', 'Daily minimum heart rate during sleep/rest', ARRAY['garmin']),
('sleep_score', 'recovery', 'score', 'Overall sleep quality score (0-100)', 'Calculated from sleep duration, efficiency, and stages', ARRAY['garmin']),
('training_load', 'performance', 'load', 'Weekly training stress accumulation', 'Sum of activity stress scores', ARRAY['garmin', 'hevy']),
('strength_progress', 'performance', 'score', 'Strength improvement tracking', 'Weighted average of lift progressions', ARRAY['hevy']),
('recovery_score', 'recovery', 'score', 'Daily recovery readiness (0-100)', 'HRV, sleep, and training load analysis', ARRAY['garmin']),
('weekly_volume', 'training', 'minutes', 'Total weekly training time', 'Sum of all training sessions', ARRAY['garmin', 'hevy']),
('body_composition', 'health', 'percent', 'Body fat percentage', 'Smart scale or DEXA measurements', ARRAY['garmin']),
('vo2_max', 'performance', 'ml/kg/min', 'Estimated VO2 max fitness level', 'Calculated from running/cycling data', ARRAY['garmin']),
('nutrition_score', 'health', 'score', 'Daily nutrition quality (0-100)', 'Macro and micronutrient balance', ARRAY['external']);

-- Insert default user preferences template
CREATE TABLE IF NOT EXISTS user_preference_templates (
    template_name VARCHAR(50) PRIMARY KEY,
    preferences JSONB NOT NULL,
    description TEXT
);

INSERT INTO user_preference_templates (template_name, preferences, description) VALUES
('default', '{
    "units": {
        "weight": "kg",
        "distance": "km",
        "temperature": "celsius"
    },
    "notifications": {
        "daily_digest": true,
        "weekly_summary": true,
        "plan_updates": true,
        "achievement_alerts": true
    },
    "privacy": {
        "data_sharing": false,
        "analytics_tracking": true,
        "export_allowed": true
    },
    "ai_preferences": {
        "planning_style": "balanced",
        "risk_tolerance": "moderate",
        "feedback_frequency": "weekly",
        "explanation_level": "detailed"
    },
    "interface": {
        "theme": "auto",
        "compact_mode": false,
        "show_advanced_metrics": false
    }
}', 'Default user preferences for new accounts'),

('athlete', '{
    "units": {
        "weight": "kg",
        "distance": "km", 
        "temperature": "celsius"
    },
    "notifications": {
        "daily_digest": true,
        "weekly_summary": true,
        "plan_updates": true,
        "achievement_alerts": true,
        "recovery_alerts": true
    },
    "privacy": {
        "data_sharing": false,
        "analytics_tracking": true,
        "export_allowed": true
    },
    "ai_preferences": {
        "planning_style": "aggressive",
        "risk_tolerance": "high",
        "feedback_frequency": "daily",
        "explanation_level": "technical"
    },
    "interface": {
        "theme": "dark",
        "compact_mode": false,
        "show_advanced_metrics": true,
        "performance_charts": true
    }
}', 'Preferences optimized for competitive athletes'),

('beginner', '{
    "units": {
        "weight": "kg",
        "distance": "km",
        "temperature": "celsius"
    },
    "notifications": {
        "daily_digest": true,
        "weekly_summary": true,
        "plan_updates": true,
        "achievement_alerts": true,
        "encouragement_messages": true
    },
    "privacy": {
        "data_sharing": false,
        "analytics_tracking": true,
        "export_allowed": true
    },
    "ai_preferences": {
        "planning_style": "conservative", 
        "risk_tolerance": "low",
        "feedback_frequency": "weekly",
        "explanation_level": "simple"
    },
    "interface": {
        "theme": "light",
        "compact_mode": false,
        "show_advanced_metrics": false,
        "guided_mode": true
    }
}', 'Simplified preferences for fitness beginners');

-- Record seed data migration
INSERT INTO schema_migrations (version, description) 
VALUES ('01_seed_data', 'Default goal templates, metric definitions, and user preference templates');