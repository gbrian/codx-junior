#!/bin/bash
echo "Downloading ollama"
cd /tmp
curl -L https://ollama.com/download/ollama-linux-amd64.tgz -o ollama-linux-amd64.tgz
echo "Decompressing..."
sudo tar -C /usr -xzf ollama-linux-amd64.tgz
