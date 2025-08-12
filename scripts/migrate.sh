#!/bin/bash

# AIthlete Database Migration Script
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
DB_HOST=${DATABASE_HOST:-localhost}
DB_PORT=${POSTGRES_PORT:-5433}
DB_NAME=${DATABASE_NAME:-aithlete}
DB_USER=${DATABASE_USER:-aithlete_user}
DB_PASSWORD=${DATABASE_PASSWORD:-aithlete_dev_password}
SCHEMA_DIR="database/schema"

echo -e "${BLUE}AIthlete Database Migration Script${NC}"
echo "=================================="

# Check if PostgreSQL is available
echo -e "${YELLOW}Checking PostgreSQL connection...${NC}"
if ! PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c "SELECT 1;" > /dev/null 2>&1; then
    echo -e "${RED}❌ Cannot connect to PostgreSQL database${NC}"
    echo "   Connection details: $DB_USER@$DB_HOST:$DB_PORT/$DB_NAME"
    echo "   Please ensure PostgreSQL is running and credentials are correct"
    exit 1
fi

echo -e "${GREEN}✅ Database connection successful${NC}"

# Check if schema directory exists
if [ ! -d "$SCHEMA_DIR" ]; then
    echo -e "${RED}❌ Schema directory not found: $SCHEMA_DIR${NC}"
    exit 1
fi

# Function to run SQL file
run_sql_file() {
    local file=$1
    local description=$2
    
    echo -e "${YELLOW}Running: $description${NC}"
    
    if PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -f "$file"; then
        echo -e "${GREEN}✅ Successfully applied: $file${NC}"
        return 0
    else
        echo -e "${RED}❌ Failed to apply: $file${NC}"
        return 1
    fi
}

# Check if migrations table exists and create if needed
echo -e "${YELLOW}Checking migration status...${NC}"
PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c "
CREATE TABLE IF NOT EXISTS schema_migrations (
    version VARCHAR(50) PRIMARY KEY,
    description TEXT,
    applied_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);" > /dev/null

# Get applied migrations
applied_migrations=$(PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -t -c "SELECT version FROM schema_migrations ORDER BY version;")

# Process schema files in order
echo -e "${YELLOW}Processing schema files...${NC}"
migration_count=0

for sql_file in $(ls $SCHEMA_DIR/*.sql | sort); do
    filename=$(basename "$sql_file")
    version=${filename%%.sql}
    
    # Check if migration is already applied
    if echo "$applied_migrations" | grep -q "^ $version$"; then
        echo -e "${BLUE}⏭️  Already applied: $filename${NC}"
        continue
    fi
    
    # Extract description from filename or file content
    if [[ "$filename" == *"_"* ]]; then
        description=${filename#*_}
        description=${description%.sql}
        description=$(echo $description | tr '_' ' ')
    else
        description="Migration $version"
    fi
    
    echo -e "${YELLOW}📄 Applying migration: $filename${NC}"
    echo "   Description: $description"
    
    if run_sql_file "$sql_file" "$description"; then
        # Record successful migration (if not already recorded in the SQL file)
        PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c "
        INSERT INTO schema_migrations (version, description) 
        VALUES ('$version', '$description')
        ON CONFLICT (version) DO NOTHING;" > /dev/null
        
        migration_count=$((migration_count + 1))
    else
        echo -e "${RED}💥 Migration failed, stopping...${NC}"
        exit 1
    fi
done

# Summary
echo ""
echo -e "${GREEN}🎉 Migration completed successfully!${NC}"
echo -e "${BLUE}   Applied $migration_count new migration(s)${NC}"

# Show current schema version
current_version=$(PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -t -c "SELECT version FROM schema_migrations ORDER BY applied_at DESC LIMIT 1;" | xargs)
echo -e "${BLUE}   Current schema version: $current_version${NC}"

# Show migration history
echo ""
echo -e "${BLUE}Migration History:${NC}"
PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c "
SELECT 
    version,
    description,
    applied_at::date as applied_date
FROM schema_migrations 
ORDER BY applied_at;"