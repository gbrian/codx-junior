echo "Build codx-junior docker"

if [ "$1" == "base" ]; then
    docker build -t codx-junior:base --target base .
else
    docker build -t codx-junior:latest .
fi