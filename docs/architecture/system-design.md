# AIthlete System Architecture

## Overview

AIthlete follows a microservices architecture with hard service boundaries, RESTful APIs, and PostgreSQL as the shared data layer. Each service is containerized and can be independently developed, tested, and deployed.

## Architecture Principles

- **Service Isolation**: Each service has a single responsibility and clear boundaries
- **Technology Flexibility**: Use the right tool for each job (Python for data integrations, Kotlin for business logic)
- **API-First**: All inter-service communication via REST APIs
- **Container-Native**: Docker containers for consistent deployment
- **Local-First**: PostgreSQL for reliable local and production deployment

## Service Architecture

### 1. Garmin Data Service (Python/Flask)
- **Responsibility**: Fetch personal health/fitness data from Garmin
- **Technology**: Python (required for python-garminconnect)
- **Database**: Stores raw Garmin data
- **API**: RESTful endpoints for data retrieval
- **Security**: Encrypted credential storage

### 2. Hevy Data Service (Python/FastAPI)
- **Responsibility**: Fetch workout data from Hevy API
- **Technology**: Python/FastAPI for consistency with Garmin service
- **Database**: Stores raw Hevy workout data
- **API**: RESTful endpoints for workout retrieval
- **Security**: Hevy Pro API key management

### 3. Data Aggregation Service (Kotlin/Spring Boot)
- **Responsibility**: Normalize and consolidate data from all sources
- **Technology**: Kotlin/Spring Boot (preferred stack)
- **Database**: Processes and stores normalized metrics
- **API**: Unified data access layer
- **Features**: Data transformation, metric calculations

### 4. User Management Service (Kotlin/Spring Boot)
- **Responsibility**: User goals, plans, preferences, progress tracking
- **Technology**: Kotlin/Spring Boot
- **Database**: User profiles, goals, plan templates
- **API**: User and goal management endpoints
- **Features**: Goal templates (weight loss, muscle gain, endurance), plan versioning

### 5. AI Planning Service (Python/FastAPI)
- **Responsibility**: Generate personalized fitness recommendations
- **Technology**: Python/FastAPI (better LLM ecosystem)
- **LLM Integration**: Provider-agnostic (OpenAI initially)
- **API**: Plan generation and recommendation endpoints
- **Features**: Context-aware planning, feedback integration

### 6. CLI Interface (Kotlin/Spring Boot)
- **Responsibility**: Primary user interaction point
- **Technology**: Kotlin/Spring Boot CLI
- **Features**: Data fetching, plan generation, interactive flows
- **Integration**: Calls all service APIs

### 7. Email Service (Kotlin/Spring Boot)
- **Responsibility**: Automated plan delivery
- **Technology**: Kotlin/Spring Boot
- **Features**: Template system, scheduled delivery, SMTP abstraction
- **Extensibility**: Pluggable template and delivery mechanisms

### 8. API Gateway (Kotlin/Spring Boot)
- **Responsibility**: Service orchestration and routing
- **Technology**: Kotlin/Spring Boot
- **Features**: Authentication, request routing, rate limiting
- **Security**: JWT token management, service-to-service auth

## Data Architecture

### PostgreSQL Schema Design
- **users**: User profiles and preferences
- **goals**: User fitness goals and templates
- **plans**: Generated fitness plans and versions
- **garmin_data**: Raw and processed Garmin metrics
- **hevy_data**: Workout data from Hevy
- **aggregated_metrics**: Normalized cross-platform data

### Data Flow
1. Data services fetch from external APIs
2. Raw data stored in respective tables
3. Data Aggregation Service normalizes and combines data
4. AI Planning Service uses aggregated data for recommendations
5. Plans stored and versioned in database

## Security Architecture

### Credential Management
- **Environment Variables**: API keys and sensitive config
- **Local Config Files**: Non-sensitive settings
- **Encrypted Storage**: User credentials (Garmin login)
- **JWT Tokens**: Inter-service authentication

### API Security
- **Authentication**: JWT-based service authentication
- **Authorization**: Role-based access control
- **Rate Limiting**: Per-service request limits
- **Input Validation**: Comprehensive request validation

## Deployment Architecture

### Development Environment
- **Docker Compose**: All services + PostgreSQL
- **Hot Reload**: Development containers with volume mounts
- **Shared Network**: Inter-service communication
- **Local Storage**: PostgreSQL data persistence

### Production Environment
- **Single Machine Deployment**: Docker containers
- **PostgreSQL**: Containerized with persistent volumes
- **Nginx**: Reverse proxy for API Gateway
- **Monitoring**: Container health checks and logging

## Technology Stack Summary

| Component | Technology | Reasoning |
|-----------|------------|-----------|
| Garmin Service | Python/Flask | Required for python-garminconnect |
| Hevy Service | Python/FastAPI | Consistency with data services |
| Data Aggregation | Kotlin/Spring Boot | Preferred stack, business logic |
| User Management | Kotlin/Spring Boot | Preferred stack, business logic |
| AI Planning | Python/FastAPI | Better LLM ecosystem |
| CLI Interface | Kotlin/Spring Boot | Preferred stack, rich CLI features |
| Email Service | Kotlin/Spring Boot | Preferred stack, template system |
| API Gateway | Kotlin/Spring Boot | Preferred stack, orchestration |
| Database | PostgreSQL | Robust, local + production ready |

## Extensibility Design

### Plugin Architecture
- **New Data Sources**: Add new services following established patterns
- **AI Providers**: Abstract LLM interface for easy provider switching
- **Delivery Channels**: Pluggable notification systems
- **Goal Types**: Template-based goal system for easy extension

### API Versioning
- **Semantic Versioning**: Service versions follow SemVer
- **Backward Compatibility**: API evolution without breaking changes
- **Contract Testing**: Ensure service compatibility