#!/bin/sh
set -e
cd /app
if [ ! -f node_modules/.bin/next ]; then
  echo "Installing npm dependencies (first run or empty volume)..."
  npm ci
fi
exec "$@"
