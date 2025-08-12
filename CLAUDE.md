# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AIthlete is a personal fitness assistant that combines personal data (Garmin, Hevy) with AI planning to suggest workouts and health actions. The project follows a microservices architecture with hard service boundaries, RESTful APIs, and PostgreSQL as the shared data layer.

## System Architecture

### Service Architecture
- **8 Microservices**: Each with single responsibility and clear boundaries
- **Technology Stack**: Kotlin/Spring Boot (business logic), Python (data integrations)
- **Database**: PostgreSQL for all persistent data
- **Deployment**: Docker containers, Docker Compose orchestration
- **APIs**: RESTful communication between all services

### Core Services
1. **Garmin Data Service** (Python/Flask) - Health/fitness data from Garmin Connect
2. **Hevy Data Service** (Python/FastAPI) - Workout data from Hevy API
3. **Data Aggregation Service** (Kotlin/Spring Boot) - Normalizes and consolidates data
4. **User Management Service** (Kotlin/Spring Boot) - User goals, plans, preferences
5. **AI Planning Service** (Python/FastAPI) - LLM-powered recommendation engine
6. **CLI Interface** (Kotlin/Spring Boot) - Primary user interaction point
7. **Email Service** (Kotlin/Spring Boot) - Automated plan delivery
8. **API Gateway** (Kotlin/Spring Boot) - Service orchestration and routing

## Development Commands

### Environment Setup
```bash
# Start all services in development mode
docker-compose up -d

# Run database migrations
./scripts/migrate.sh

# Build all services
./scripts/build.sh

# Run all tests
./scripts/test.sh
```

### Service Development
```bash
# Start individual service for development
docker-compose up garmin-service
docker-compose up user-service

# View service logs
docker-compose logs -f [service-name]

# Run tests for specific service
./scripts/test-service.sh [service-name]
```

## Epic-Based Development

Project is organized into 9 measurable epics:

1. **Foundation Infrastructure** (2-3 weeks) - Database, Docker, CI/CD, templates
2. **Garmin Data Integration** (1-2 weeks) - Python service with garmin-connect
3. **Hevy Data Integration** (1 week) - Hevy API integration
4. **User Goals & Planning** (2 weeks) - Goal templates, plan versioning
5. **AI Planning Engine** (2-3 weeks) - LLM integration, recommendation algorithms
6. **CLI Interface** (1-2 weeks) - Command-line user interface
7. **Email Digest System** (1 week) - Automated plan delivery
8. **Integration & Orchestration** (1-2 weeks) - API Gateway, end-to-end testing
9. **Deployment & Operations** (1 week) - Production configuration, monitoring

**Current Status**: Planning complete, ready to begin Epic 1

## Architecture Documentation

Detailed documentation available in:
- `docs/architecture/system-design.md` - Complete system architecture
- `docs/epics/development-plan.md` - Detailed epic breakdown with acceptance criteria  
- `docs/status/project-status.md` - Current project status and progress tracking

## Commit Conventions

This project follows [Conventional Commits](https://www.conventionalcommits.org) with Semantic Versioning:

- `feat(scope): description` - new features
- `fix(scope): description` - bug fixes
- `docs: description` - documentation changes
- `refactor: description` - code changes without new features or fixes
- `test: description` - test additions/updates
- `chore: description` - maintenance tasks

Common scopes: `garmin`, `hevy`, `email`, `cli`, `ai`

## Data Sources & APIs

- **Garmin**: Via python-garminconnect (personal use, respect ToS)
- **Hevy**: Official API at api.hevyapp.com (requires Pro subscription)
- **MCP**: Model Context Protocol for AI-tool communication

## Privacy & Compliance

- Personal use only
- Respect third-party Terms of Service
- Local-first data storage approach
- No medical claims or advice