package com.aithlete.shared.auth

/**
 * Security constants shared across all services
 */
object SecurityConstants {
    
    // JWT Constants
    const val JWT_HEADER = "Authorization"
    const val JWT_PREFIX = "Bearer "
    const val JWT_EXPIRATION_TIME = 86400 // 24 hours in seconds
    
    // User Roles
    const val ROLE_USER = "ROLE_USER"
    const val ROLE_ADMIN = "ROLE_ADMIN"
    const val ROLE_SERVICE = "ROLE_SERVICE"
    
    // Public Endpoints (no authentication required)
    val PUBLIC_ENDPOINTS = arrayOf(
        "/actuator/**",
        "/swagger-ui/**",
        "/v3/api-docs/**",
        "/health",
        "/",
        "/api/v1/auth/**"
    )
    
    // Service Endpoints (service-to-service communication)
    val SERVICE_ENDPOINTS = arrayOf(
        "/api/v1/internal/**"
    )
    
    // User Endpoints (user authentication required)
    val USER_ENDPOINTS = arrayOf(
        "/api/v1/**"
    )
    
    // Password Requirements
    const val MIN_PASSWORD_LENGTH = 8
    const val PASSWORD_PATTERN = "^(?=.*[a-z])(?=.*[A-Z])(?=.*\\d)(?=.*[@\$!%*?&])[A-Za-z\\d@\$!%*?&]{8,}$"
    
    // Rate Limiting
    const val DEFAULT_RATE_LIMIT = 100 // requests per minute
    const val AUTH_RATE_LIMIT = 10 // authentication attempts per minute
    
    // Session Management
    const val SESSION_TIMEOUT = 1800 // 30 minutes in seconds
    const val MAX_CONCURRENT_SESSIONS = 5
    
    // Encryption
    const val AES_KEY_LENGTH = 256
    const val AES_TRANSFORMATION = "AES/GCM/NoPadding"
    const val PBKDF2_ITERATIONS = 10000
}