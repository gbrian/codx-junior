#!/bin/bash
set -e

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "⚠️  No .env file found. Copying from .env.example..."
    cp .env.example .env
    echo "📝 Please edit .env and set CODX_JUNIOR_MODEL_NAME before running."
    exit 1
fi

# Check if models directory exists and has at least one .gguf file
if [ ! -d "models" ] || [ -z "$(ls models/*.gguf 2>/dev/null)" ]; then
    echo "⚠️  No GGUF model found in ./models/"
    echo "📥 Please download a model and place it in the models/ directory."
    echo ""
    echo "Example (SmolLM-135M):"
    echo "  wget -P models/ https://huggingface.co/HuggingFaceTB/SmolLM-135M-Instruct-GGUF/resolve/main/smollm-135m-instruct.Q4_K_M.gguf"
    exit 1
fi

echo "🚀 Starting codx-junior..."
docker-compose -f docker/docker-compose.yml up