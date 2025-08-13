#!/bin/bash

# Epic 2 Testing Script
# Usage: ./test-epic-2.sh YOUR_GARMIN_USERNAME YOUR_GARMIN_PASSWORD

set -e

if [ $# -ne 2 ]; then
    echo "Usage: $0 <garmin_username> <garmin_password>"
    echo "Example: $0 john@example.com mypassword"
    exit 1
fi

GARMIN_USERNAME="$1"
GARMIN_PASSWORD="$2"
USER_ID="test-user-$(date +%s)"
BASE_URL="http://localhost:8003"

echo "🧪 Testing Epic 2: Garmin Data Integration"
echo "User ID: $USER_ID"
echo ""

# Check service health
echo "1️⃣ Checking service health..."
curl -s "$BASE_URL/health" | jq . || echo "Service not responding"
echo ""

# Store credentials
echo "2️⃣ Storing Garmin credentials..."
STORE_RESPONSE=$(curl -s -X POST "$BASE_URL/api/v1/credentials?user_id=$USER_ID" \
  -H "Content-Type: application/json" \
  -d "{\"username\": \"$GARMIN_USERNAME\", \"password\": \"$GARMIN_PASSWORD\"}")

echo "$STORE_RESPONSE" | jq .
echo ""

# Check sync status
echo "3️⃣ Checking sync status..."
curl -s "$BASE_URL/api/v1/sync/status?user_id=$USER_ID" | jq .
echo ""

# Sync data
echo "4️⃣ Syncing Garmin data (last 3 days)..."
SYNC_RESPONSE=$(curl -s -X POST "$BASE_URL/api/v1/sync?user_id=$USER_ID&days=3")
echo "$SYNC_RESPONSE" | jq .
echo ""

# Get activities
echo "5️⃣ Retrieving activities..."
curl -s "$BASE_URL/api/v1/activities?user_id=$USER_ID&days=3&limit=5" | jq '.activities | length as $count | "Found \($count) activities"'
echo ""

# Get health summary
echo "6️⃣ Getting health summary..."
curl -s "$BASE_URL/api/v1/health/summary?user_id=$USER_ID&days=3" | jq '.summary | keys | "Health metrics: \(join(", "))"'
echo ""

# Check sync status after sync
echo "7️⃣ Final sync status..."
curl -s "$BASE_URL/api/v1/sync/status?user_id=$USER_ID" | jq .
echo ""

# Clean up credentials
echo "8️⃣ Cleaning up test credentials..."
curl -s -X DELETE "$BASE_URL/api/v1/credentials?user_id=$USER_ID" | jq .
echo ""

echo "✅ Epic 2 testing completed successfully!"
echo "🔒 Test credentials have been removed for security."