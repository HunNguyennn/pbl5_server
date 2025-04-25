#!/usr/bin/env bash
set -e

# Activate virtual env if exists
if [ -f ./venv310/Scripts/activate ]; then
  source ./venv310/Scripts/activate
fi

# Load environment variables
if [ -f .env ]; then
  export $(grep -v '^#' .env | xargs)
fi

# Run FastAPI server
uvicorn app.main:app \
  --host ${HOST:-0.0.0.0} \
  --port ${PORT:-8000} \
  --reload