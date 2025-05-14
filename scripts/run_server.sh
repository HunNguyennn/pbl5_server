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

# Set default values for host to be localhost for secure context
HOST=${HOST:-127.0.0.1}
PORT=${PORT:-8000}

# Display server configuration
echo "Starting server with configuration:"
echo "Host: $HOST" 
echo "Port: $PORT"
echo "Secure context available: Yes (localhost)"

# Run FastAPI server
uvicorn app.main:app \
  --host $HOST \
  --port $PORT \
  --reload