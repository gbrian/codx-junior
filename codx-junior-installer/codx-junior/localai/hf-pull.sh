#!/usr/bin/env bash

# Exit immediately if any command fails
set -euo pipefail

# Check if model string was provided
if [ $# -eq 0 ]; then
    echo "❌ Error: Missing model identifier."
    echo "Usage: $0 <username/repo-name/filename.gguf> or <username/repo-name> or <username/repo-name/subfolder/filename.gguf>"
    echo "Example: $0 google/gemma-2-9b-it-GGUF/gemma-2-9b-it-Q4_K_M.gguf"
    echo "Example: $0 nerkyor/Qwen3.6-27B-Uncensored-Heretic-DSV4Pro-GLM52-SFT-GPT55-RL-Coding-VL-MTP-GGUF/Q8_0/Qwen3.6-27B-Uncensored-Heretic-Q8_0.gguf"
    exit 1
fi

INPUT_STRING="$1"

# Parse the components using bash string manipulation
SLASH_COUNT=$(tr -cd '/' <<< "$INPUT_STRING" | wc -c)

if [ "$SLASH_COUNT" -eq 1 ]; then
    # Format: username/repo (downloads entire repo)
    REPO_ID="$INPUT_STRING"
    FILE_PATH=""
    echo "📂 Target: Entire repository detected."
elif [ "$SLASH_COUNT" -ge 2 ]; then
    # Format: username/repo/... (can have multiple path parts for subfolders)
    # Extract first two parts as REPO_ID, rest as FILE_PATH
    REPO_ID=$(echo "$INPUT_STRING" | cut -d'/' -f1-2)
    FILE_PATH=$(echo "$INPUT_STRING" | cut -d'/' -f3-)
    echo "🎯 Target: Specific file in a repository detected."
else
    echo "❌ Error: Invalid format. Must be 'user/repo' or 'user/repo/file.gguf' or 'user/repo/subfolder/file.gguf'"
    exit 1
fi

echo "🚀 Repository ID : $REPO_ID"
if [ -n "$FILE_PATH" ]; then
    echo "📄 File Path     : $FILE_PATH"
fi

# Install Hugging Face CLI if not installed
if ! command -v hf &>/dev/null; then
    echo "📦 Hugging Face CLI (hf) not found. Installing..."
    pip install huggingface-cli
    if ! command -v hf &>/dev/null; then
        echo "❌ Error: Failed to install hf."
        exit 1
    fi
fi

# Ensure target directory exists
mkdir -p /build/models

echo "⏳ Triggering high-speed download..."
echo "--------------------------------------------------------"

# Execute the download command
if [ -n "$FILE_PATH" ]; then
    # Download single file (with possible subfolders) from a repository
    REPO_FOLDER=$(echo "$REPO_ID" | tr '/' '-')
    FILENAME=$(basename "$FILE_PATH")
    
    hf download \
      "$REPO_ID" \
      --include "$FILE_PATH" \
      --local-dir "/build/models/${REPO_FOLDER}"

    # Generate the LocalAI model alias name (stripping the .gguf extension)
    MODEL_ALIAS="${FILENAME%.gguf}"
    CONFIG_FILE="${MODEL_ALIAS}.yaml"
    
    echo "📝 Generating LocalAI configuration file for $MODEL_ALIAS..."
    # Drop the YAML file directly into the shared /build/models directory
    cat << EOF > "/build/models/${CONFIG_FILE}"
name: ${MODEL_ALIAS}
parameters:
  model: ${REPO_FOLDER}/${FILE_PATH}
EOF

else
    # Download entire folder (e.g., embeddings or safetensors models)
    FOLDER_NAME=$(echo "$REPO_ID" | tr '/' '-')
    CONFIG_FILE="${FOLDER_NAME}.yaml"
    hf download \
      "$REPO_ID" \
      --local-dir "/build/models/${FOLDER_NAME}"

    echo "📝 Generating LocalAI configuration file for ${FOLDER_NAME}..."
    # Drop the YAML file pointing to the directory name for transformers backends
    cat << EOF > "/build/models/${CONFIG_FILE}"
name: ${FOLDER_NAME}
parameters:
  model: ${FOLDER_NAME}
EOF
fi

COMMAND="cat /build/models/${CONFIG_FILE}"
echo "COMMAND: $COMMAND"
$COMMAND

echo "--------------------------------------------------------"
echo "✅  Done! The file and its YAML config are ready inside your LocalAI volume."
echo "🔄 LocalAI will auto-load the new configuration instantly."