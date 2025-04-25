#!/usr/bin/env bash
set -e

echo "Initializing database..."
python - << 'EOF'
from app.dashboard import init_database
init_database()
EOF

echo "Database initialized."