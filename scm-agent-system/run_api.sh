#!/bin/bash
# run_api.sh
# Gunicorn + Uvicorn 고속 비동기 추론 엔진 구동
echo "🎬 Starting SCM ML High-Performance serving container (Gunicorn + Uvicorn)..."
gunicorn api:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000 --timeout 120
