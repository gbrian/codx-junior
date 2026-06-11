#!/bin/bash
set -e

echo "🛑 Stopping codx-junior..."
docker-compose -f docker/docker-compose.yml down

echo "✅ Stopped."