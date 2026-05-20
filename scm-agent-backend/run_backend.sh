#!/bin/bash
# Move to the directory where this script is located
cd "$(dirname "$0")"

# Ensure Docker binary path is in the PATH environment variable
export PATH="$PATH:/usr/local/bin:/Applications/Docker.app/Contents/Resources/bin"

# Check if Docker is running
if ! docker info >/dev/null 2>&1; then
    echo "🐳 Docker is not running. Launching Docker Desktop..."
    open -a Docker
    echo "⏳ Waiting for Docker daemon to start (this may take a moment)..."
    until docker info >/dev/null 2>&1; do
        sleep 2
    done
    echo "🐳 Docker is now running!"
fi

echo "🐘 Starting PostgreSQL DB and SCM analysis microservices..."
docker compose up -d --build

echo "✅ Backend status:"
docker compose ps
