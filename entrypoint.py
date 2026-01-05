import os
import sys

# Get port from environment variable or use default
port = int(os.getenv("PORT", "8000"))

print(f"🚀 Starting Font Extractor API on port {port}...", file=sys.stderr)
print(f"📍 Environment: PORT={port}", file=sys.stderr)
print(f"🐍 Python version: {sys.version}", file=sys.stderr)

# Import and run uvicorn
import uvicorn

uvicorn.run(
    "main:app",
    host="0.0.0.0",
    port=port,
    log_level="info"
)
