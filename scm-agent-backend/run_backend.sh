#!/bin/bash
# Move to the directory where this script is located
cd "$(dirname "$0")"

# Export default SCM database credentials matching docker-compose.yml
export DB_URL="jdbc:postgresql://localhost:5432/scm_enterprise"
export DB_USERNAME="scm_admin"
export DB_PASSWORD="scm_secret_password"
export OPENAI_API_KEY="${OPENAI_API_KEY:-sk-dummy-local-key}"

echo "☕ [SCM Backend] Launching SCM Enterprise Java Spring Boot Backend..."

echo "🐳 [SCM Database] Ensuring PostgreSQL is running via Docker..."
docker-compose up -d postgres || echo "⚠️ Warning: docker-compose failed. Please ensure Docker Desktop is running!"

echo "☕ [SCM Backend] 1. Launching FastAPI Analysis Microservice on Port 8090..."

# Start FastAPI Microservice in the background
cd analysis-microservice
../../venv/bin/python -m uvicorn main:app --port 8090 --host 0.0.0.0 > ../fastapi_analysis.log 2>&1 &
FASTAPI_PID=$!
cd ..

echo "✅ FastAPI Analysis Microservice started in background (PID: $FASTAPI_PID, Log: fastapi_analysis.log)"
echo "☕ [SCM Backend] 2. Launching Java Spring Boot on Port 8080..."

# Clean stale build artifacts before compiling
rm -rf build/classes build/generated build/tmp

# Run Spring Boot using Gradle Wrapper (JDK 17 Toolchain auto-provisioning enabled)
./gradlew bootRun --no-daemon

# Cleanup on exit
trap "kill $FASTAPI_PID" EXIT
