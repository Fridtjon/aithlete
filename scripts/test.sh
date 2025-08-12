#!/bin/bash

# AIthlete Test Script
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}AIthlete Test Script${NC}"
echo "==================="

# Services to test
KOTLIN_SERVICES=("api-gateway" "user-service" "data-aggregation-service" "email-service" "cli-interface")
PYTHON_SERVICES=("garmin-service" "hevy-service" "ai-planning-service")

# Test results
PASSED_TESTS=0
FAILED_TESTS=0
TOTAL_SERVICES=0

test_kotlin_service() {
    local service=$1
    local service_dir="services/$service"
    
    if [ ! -d "$service_dir" ]; then
        echo -e "${YELLOW}⏭️  Service not found: $service${NC}"
        return 0
    fi
    
    TOTAL_SERVICES=$((TOTAL_SERVICES + 1))
    echo -e "${YELLOW}🧪 Testing Kotlin service: $service${NC}"
    
    cd "$service_dir"
    
    if [ -f "gradlew" ]; then
        # Run tests
        if ./gradlew test --no-daemon; then
            echo -e "${GREEN}✅ Tests passed: $service${NC}"
            PASSED_TESTS=$((PASSED_TESTS + 1))
        else
            echo -e "${RED}❌ Tests failed: $service${NC}"
            FAILED_TESTS=$((FAILED_TESTS + 1))
            cd - > /dev/null
            return 1
        fi
        
        # Run integration tests if they exist
        if ./gradlew integrationTest --no-daemon 2>/dev/null; then
            echo -e "${GREEN}✅ Integration tests passed: $service${NC}"
        fi
    else
        echo -e "${YELLOW}⚠️  No gradlew found for: $service${NC}"
    fi
    
    cd - > /dev/null
}

test_python_service() {
    local service=$1
    local service_dir="services/$service"
    
    if [ ! -d "$service_dir" ]; then
        echo -e "${YELLOW}⏭️  Service not found: $service${NC}"
        return 0
    fi
    
    TOTAL_SERVICES=$((TOTAL_SERVICES + 1))
    echo -e "${YELLOW}🐍 Testing Python service: $service${NC}"
    
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
        pip install -q -r requirements.txt
        if [ -f "requirements-dev.txt" ]; then
            pip install -q -r requirements-dev.txt
        fi
    fi
    
    # Run tests if pytest is available and tests directory exists
    if command -v pytest >/dev/null 2>&1 && [ -d "tests" ]; then
        echo -e "${BLUE}Running pytest...${NC}"
        if pytest -v; then
            echo -e "${GREEN}✅ Tests passed: $service${NC}"
            PASSED_TESTS=$((PASSED_TESTS + 1))
        else
            echo -e "${RED}❌ Tests failed: $service${NC}"
            FAILED_TESTS=$((FAILED_TESTS + 1))
            deactivate
            cd - > /dev/null
            return 1
        fi
    else
        echo -e "${YELLOW}⚠️  No tests found for: $service${NC}"
    fi
    
    # Run linting
    if command -v flake8 >/dev/null 2>&1; then
        echo -e "${BLUE}Running flake8...${NC}"
        if flake8; then
            echo -e "${GREEN}✅ Linting passed: $service${NC}"
        else
            echo -e "${RED}❌ Linting failed: $service${NC}"
        fi
    fi
    
    # Deactivate virtual environment
    deactivate
    
    cd - > /dev/null
}

run_integration_tests() {
    echo -e "${YELLOW}🔗 Running integration tests...${NC}"
    
    # Start test services
    if command -v docker-compose >/dev/null 2>&1; then
        echo -e "${BLUE}Starting test environment...${NC}"
        
        # Create test environment file
        cp .env.example .env.test
        echo "DATABASE_PASSWORD=test_password" >> .env.test
        echo "JWT_SECRET=test_jwt_secret" >> .env.test
        
        # Start PostgreSQL and Redis for integration tests
        if docker-compose -f docker-compose.yml --env-file .env.test up -d postgres redis; then
            echo -e "${GREEN}✅ Test services started${NC}"
            
            # Wait for services to be ready
            sleep 10
            
            # Run database migrations
            if ./scripts/migrate.sh; then
                echo -e "${GREEN}✅ Database migrations applied${NC}"
            else
                echo -e "${RED}❌ Database migrations failed${NC}"
                return 1
            fi
            
            # Test database connectivity
            if docker-compose --env-file .env.test exec -T postgres pg_isready -U aithlete_user -d aithlete; then
                echo -e "${GREEN}✅ Database connectivity test passed${NC}"
            else
                echo -e "${RED}❌ Database connectivity test failed${NC}"
                return 1
            fi
            
            # Test Redis connectivity
            if docker-compose --env-file .env.test exec -T redis redis-cli ping; then
                echo -e "${GREEN}✅ Redis connectivity test passed${NC}"
            else
                echo -e "${RED}❌ Redis connectivity test failed${NC}"
                return 1
            fi
            
            # Clean up
            echo -e "${BLUE}Cleaning up test environment...${NC}"
            docker-compose --env-file .env.test down -v
            rm -f .env.test
            
        else
            echo -e "${RED}❌ Failed to start test services${NC}"
            return 1
        fi
    else
        echo -e "${YELLOW}⚠️  Docker Compose not available, skipping integration tests${NC}"
    fi
}

# Main test process
echo -e "${BLUE}Running all tests...${NC}"

# Test Kotlin services
echo -e "${BLUE}Phase 1: Kotlin/Spring Boot Services${NC}"
for service in "${KOTLIN_SERVICES[@]}"; do
    test_kotlin_service "$service"
done

# Test Python services
echo -e "${BLUE}Phase 2: Python/FastAPI Services${NC}"
for service in "${PYTHON_SERVICES[@]}"; do
    test_python_service "$service"
done

# Run integration tests
echo -e "${BLUE}Phase 3: Integration Tests${NC}"
run_integration_tests

# Summary
echo ""
echo -e "${BLUE}Test Summary${NC}"
echo "============"
echo -e "${GREEN}✅ Services passed: $PASSED_TESTS${NC}"
echo -e "${RED}❌ Services failed: $FAILED_TESTS${NC}"
echo -e "${BLUE}📊 Total services tested: $TOTAL_SERVICES${NC}"

if [ $FAILED_TESTS -eq 0 ]; then
    echo ""
    echo -e "${GREEN}🎉 All tests passed successfully!${NC}"
    exit 0
else
    echo ""
    echo -e "${RED}💥 Some tests failed${NC}"
    exit 1
fi