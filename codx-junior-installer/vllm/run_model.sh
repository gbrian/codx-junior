MODEL=${1:-Qwen/Qwen2.5-1.5B-Instruct}
PORT=${2:-8000}

docker run -d --rm \
  --name vllm-coder \
  --network codx-junior_default \
  -p ${PORT}:8000 \
  -v ./.cache/huggingface:/root/.cache/huggingface \
  --ipc=host \
  -e VLLM_CPU_KVCACHE_SPACE=40 \
  -e VLLM_CPU_OMP_THREADS_BIND=auto \
  vllm/vllm-openai-cpu:latest-x86_64 \
  --model ${MODEL} \
  --host 0.0.0.0 \
  --port 8000 \
  --dtype float16