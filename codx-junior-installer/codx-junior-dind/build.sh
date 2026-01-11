# Build codx-junior:dind
echo "Build codx-junior-dind"
cd .. && docker build -t codx-junior:dind -f codx-junior-dind/Dockerfile .
