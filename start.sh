#!/bin/sh

# Get port from environment or use default
PORT=${PORT:-8000}

echo "Starting Font Extractor API on port $PORT..."
echo "Environment: PORT=$PORT"

# Start uvicorn with the dynamic port
exec uvicorn main:app --host 0.0.0.0 --port $PORT
