#/bin/bash

# Ollama
curl http://ollama-codx-junior:11434/api/pull -d '{
  "model": "phi4"
}'

curl http://ollama-codx-junior:11434/api/pull -d '{
  "model": "gemma3"
}'

