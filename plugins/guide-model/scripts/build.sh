#!/bin/bash
set -e

echo "🔨 Building codx-junior Docker image..."
docker-compose -f docker/docker-compose.yml build --no-cache

echo "✅ Build complete!"