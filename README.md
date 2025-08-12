# README — AIthlete (working title)

## Project summary
AIthlete is a personal fitness assistant that combines your own data (e.g., Garmin and Hevy) with an AI planner to suggest workouts and health actions for the day, week, and month. The project is intentionally modular: small tools (data fetchers and action performers) communicate via simple APIs, while an AI layer orchestrates them to create plans and deliver updates.

- Garmin data will be accessed via the community Python wrapper python-garminconnect (personal use). 

- Hevy data will be accessed via Hevy’s official API (Pro users). api.hevyapp.com

- An AI “agent” sits on top and asks tools for what it needs (potentially via MCP – Model Context Protocol). 

Note: This project is for personal use. Respect platform Terms of Service and privacy expectations when using any third-party tools.

## Goals
- Simple to run: one command to start; sensible defaults.
- Simple to understand: small, well-named modules with clear contracts.
- Simple to deploy: containerized components; minimal external dependencies.
- Easy to extend: add a new tool or data source without touching existing ones.
- Language agnostic: all tools communicate over API
- AI-first usage: the agent can request data or trigger actions through the same interfaces as a user would.

## What this project does (high level)
- Collects personal health/fitness data (activities, heart rate, sleep, weight, etc.) from Garmin; gym workouts from Hevy.
- Normalizes data into consistent, minimal shapes that are easy to reason about.
- Plans: the AI proposes daily/weekly/monthly training and recovery actions based on your recent metrics and goals.
- Delivers: plans are available via CLI and optional scheduled email digests (daily + weekly).

## Philosophy
- Small modules, thin APIs. Each tool does one thing well (fetch data or perform an action) and exposes a tiny interface (REST or similar).
- Orchestration is pluggable. We may use a lightweight orchestrator; details are intentionally left open.
- Protocol-friendly. MCP is a candidate to let the AI call tools in a standardized way. 
- Containers by default. Each tool can run in its own container.
- Local-first. Prefer local storage of your data; cloud is optional.

## Initial focus tools
- Garmin tool: uses python-garminconnect to fetch personal health and activity data. 
- Hevy tool: uses Hevy’s official API (requires Hevy Pro key). 

## Interfaces
- CLI to ask the agent for a plan and to run ad-hoc fetches.
- Email digests (daily, weekly) with your plan and key insights.
- APIs between tools (REST or similar) so modules can talk to each other and to the AI.

## Non-goals (for now)
- Making medical claims or giving medical advice.
- Multi-user SaaS features.
- Locking into a single vendor or architecture.

## Technical Architecture

AIthlete is built as a microservices system with 8 core services:

### Service Architecture
- **Technology Stack**: Kotlin/Spring Boot (business logic), Python (data integrations)
- **Database**: PostgreSQL for all persistent data
- **Communication**: RESTful APIs between services
- **Deployment**: Docker containers with Docker Compose orchestration

### Core Services
1. **Garmin Data Service** (Python) - Fetches health/fitness data via python-garminconnect
2. **Hevy Data Service** (Python) - Integrates with Hevy Pro API for workout data  
3. **Data Aggregation Service** (Kotlin) - Normalizes data from all sources
4. **User Management Service** (Kotlin) - Manages user goals, plans, and preferences
5. **AI Planning Service** (Python) - Generates personalized recommendations using LLMs
6. **CLI Interface** (Kotlin) - Primary user interaction point
7. **Email Service** (Kotlin) - Automated digest delivery system
8. **API Gateway** (Kotlin) - Service orchestration and routing

### Development Approach
The project is organized into **9 measurable epics** spanning 12-16 weeks:
- Foundation Infrastructure → Data Integration → AI Planning → User Interface → Production Deployment

Detailed documentation available in `docs/` folder.

## Roadmap

### Phase 1: Foundation (Weeks 1-3)
- PostgreSQL schema design and Docker environment setup
- Service templates and CI/CD pipeline

### Phase 2: Data Integration (Weeks 4-6)  
- Garmin and Hevy data services with normalization
- User goal and plan management system

### Phase 3: Intelligence Layer (Weeks 7-10)
- AI planning engine with LLM integration
- Command-line interface for user interactions

### Phase 4: Delivery & Operations (Weeks 11-16)
- Email digest system and service orchestration
- Production deployment and monitoring

## Conventional Commits & Versioning

This project follows the [Conventional Commits](https://www.conventionalcommits.org) specification for commit messages.

### Why?
- Makes commit history more readable.
- Enables automated versioning and changelog generation.
- Ensures consistent communication of changes.

### Commit Message Format
```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

**Examples:**
```
feat(garmin): add ability to fetch resting heart rate data
fix(email): correct daily plan subject line
docs: update README with conventional commits section
```

### Common Commit Types
- feat – a new feature.
- fix – a bug fix.
- docs – documentation only changes.
- style – changes that do not affect meaning (whitespace, formatting).
- refactor – code change that neither fixes a bug nor adds a feature.
- perf – performance improvement.
- test – adding or updating tests.
- chore – maintenance tasks, build scripts, CI config changes.

### Versioning
We use [Semantic Versioning (SemVer)](https://semver.org/):


```
MAJOR.MINOR.PATCH
```

- MAJOR – breaking changes.
- MINOR – backward-compatible features.
- PATCH – backward-compatible bug fixes.

When combined with Conventional Commits, tools like semantic-release can automatically bump versions and generate changelogs based on commit messages.