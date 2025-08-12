#!/bin/bash

# AIthlete Build Script
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}AIthlete Build Script${NC}"
echo "===================="

# Services to build
KOTLIN_SERVICES=("api-gateway" "user-service" "data-aggregation-service" "email-service" "cli-interface")
PYTHON_SERVICES=("garmin-service" "hevy-service" "ai-planning-service")

build_kotlin_service() {
    local service=$1
    local service_dir="services/$service"
    
    if [ ! -d "$service_dir" ]; then
        echo -e "${YELLOW}⏭️  Service not found: $service${NC}"
        return 0
    fi
    
    echo -e "${YELLOW}🔨 Building Kotlin service: $service${NC}"
    
    cd "$service_dir"
    
    if [ -f "gradlew" ]; then
        ./gradlew clean build --no-daemon
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}✅ Successfully built: $service${NC}"
        else
            echo -e "${RED}❌ Failed to build: $service${NC}"
            return 1
        fi
    else
        echo -e "${YELLOW}⚠️  No gradlew found for: $service${NC}"
    fi
    
    cd - > /dev/null
}

build_python_service() {
    local service=$1
    local service_dir="services/$service"
    
    if [ ! -d "$service_dir" ]; then
        echo -e "${YELLOW}⏭️  Service not found: $service${NC}"
        return 0
    fi
    
    echo -e "${YELLOW}🐍 Building Python service: $service${NC}"
    
    cd "$service_dir"
    
    # Create virtual environment if it doesn't exist
    if [ ! -d "venv" ]; then
        echo -e "${BLUE}Creating virtual environment...${NC}"
        python3 -m venv venv
    fi
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Install dependencies
    if [ -f "requirements.txt" ]; then
        echo -e "${BLUE}Installing dependencies...${NC}"
        pip install --upgrade pip
        pip install -r requirements.txt
        
        if [ -f "requirements-dev.txt" ]; then
            pip install -r requirements-dev.txt
        fi
    fi
    
    # Run linting and type checking
    if command -v flake8 >/dev/null 2>&1; then
        echo -e "${BLUE}Running flake8...${NC}"
        flake8
    fi
    
    if command -v mypy >/dev/null 2>&1; then
        echo -e "${BLUE}Running mypy...${NC}"
        mypy . --ignore-missing-imports || true
    fi
    
    # Deactivate virtual environment
    deactivate
    
    echo -e "${GREEN}✅ Successfully processed: $service${NC}"
    cd - > /dev/null
}

build_docker_images() {
    echo -e "${YELLOW}🐳 Building Docker images...${NC}"
    
    if command -v docker >/dev/null 2>&1; then
        # Build all services with Docker Compose
        if docker-compose build; then
            echo -e "${GREEN}✅ Docker images built successfully${NC}"
        else
            echo -e "${RED}❌ Failed to build Docker images${NC}"
            return 1
        fi
    else
        echo -e "${YELLOW}⚠️  Docker not available, skipping image build${NC}"
    fi
}

# Main build process
echo -e "${BLUE}Building all services...${NC}"

# Build Kotlin services
echo -e "${BLUE}Phase 1: Kotlin/Spring Boot Services${NC}"
for service in "${KOTLIN_SERVICES[@]}"; do
    build_kotlin_service "$service"
done

# Build Python services
echo -e "${BLUE}Phase 2: Python/FastAPI Services${NC}"
for service in "${PYTHON_SERVICES[@]}"; do
    build_python_service "$service"
done

# Build Docker images
echo -e "${BLUE}Phase 3: Docker Images${NC}"
build_docker_images

echo ""
echo -e "${GREEN}🎉 Build completed successfully!${NC}"
echo -e "${BLUE}All services are ready for deployment${NC}"