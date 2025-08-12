# AIthlete Shared Authentication

This directory contains shared authentication utilities used across all AIthlete services.

## Structure

```
shared/auth/
├── kotlin/           # Shared utilities for Kotlin/Spring Boot services
│   ├── JwtUtils.kt
│   └── SecurityConstants.kt
├── python/           # Shared utilities for Python/FastAPI services
│   ├── __init__.py
│   └── jwt_utils.py
└── README.md
```

## Usage

### Kotlin Services

Copy the Kotlin files to your service's shared package and use them:

```kotlin
@Component
class AuthService(private val jwtUtils: JwtUtils) {
    
    fun authenticateUser(username: String, userId: String): String {
        return jwtUtils.generateToken(username, userId)
    }
    
    fun validateRequest(authHeader: String): String? {
        val token = JwtUtils.extractTokenFromHeader(authHeader)
        return if (token != null && jwtUtils.validateToken(token)) {
            jwtUtils.getUsernameFromToken(token)
        } else null
    }
}
```

### Python Services

Copy the Python module to your service and use it:

```python
from shared.auth import JWTUtils, SecurityConstants

jwt_utils = JWTUtils(secret_key="your-secret-key")

# Generate token
token = jwt_utils.generate_token("username", "user_id")

# Validate token
if jwt_utils.validate_token(token):
    username = jwt_utils.get_username_from_token(token)
    user_id = jwt_utils.get_user_id_from_token(token)
```

### FastAPI Dependencies

For FastAPI services, use the provided dependency:

```python
from fastapi import Depends, HTTPException, Header
from shared.auth import get_current_user_from_token, JWTUtils

jwt_utils = JWTUtils(secret_key="your-secret-key")

@app.get("/protected")
async def protected_endpoint(
    authorization: str = Header(None),
    current_user: dict = Depends(lambda: get_current_user_from_token(authorization, jwt_utils))
):
    return {"user": current_user["username"]}
```

## Features

### JWT Token Management
- Token generation with configurable expiration
- Token validation and parsing
- Username and user ID extraction
- Secure token signing with HMAC-SHA256

### Credential Encryption
- AES encryption for storing sensitive user credentials
- PBKDF2 key derivation with salt
- Secure storage for Garmin, Hevy, and other service credentials

### Security Constants
- Standardized security configurations
- Public/private endpoint definitions
- Rate limiting configurations
- Password policy enforcement

## Security Considerations

1. **Secret Key Management**: Use environment variables for JWT secrets
2. **Token Expiration**: Configure appropriate token lifetimes
3. **Rate Limiting**: Implement rate limiting for authentication endpoints
4. **HTTPS Only**: Always use HTTPS in production
5. **Credential Storage**: Never store credentials in plaintext

## Environment Variables

Required environment variables for all services:

```bash
JWT_SECRET=your-strong-jwt-secret-here
DATABASE_URL=your-database-connection-string
REDIS_URL=your-redis-connection-string
```

## Integration with Services

Each service should:

1. Copy the appropriate authentication utilities
2. Configure JWT secret in application properties/settings
3. Implement authentication middleware/filters
4. Use the utilities for token generation and validation
5. Protect endpoints according to security requirements