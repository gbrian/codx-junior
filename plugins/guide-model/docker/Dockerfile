FROM python:3.11-slim

# Install build dependencies for llama-cpp-python
RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml .
RUN pip install --no-cache-dir .

COPY . .

# Create directories for models and guides
RUN mkdir -p /app/models /app/guides

CMD ["python", "-m", "codx.junior"]