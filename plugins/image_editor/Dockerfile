# Multi-stage build to minimize final image size
FROM python:3.11-slim as builder

# Install system dependencies required for building
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy project files
WORKDIR /build
COPY pyproject.toml README.md ./
COPY image_cli.py ./

# Install Python dependencies in virtual environment
RUN pip install --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -e .

# Production stage
FROM python:3.11-slim

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Set environment variables for HuggingFace cache
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    HF_HOME="/cache/huggingface" \
    TRANSFORMERS_CACHE="/cache/huggingface/transformers" \
    HF_DATASETS_CACHE="/cache/huggingface/datasets"

# Create cache directory
RUN mkdir -p /cache/huggingface

# Create non-root user for security
RUN useradd -m -u 1000 imageuser

# Set working directory
WORKDIR /workspace
RUN chown -R imageuser:imageuser /workspace /cache

# Switch to non-root user
USER imageuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import torch; print('OK')" || exit 1

# Entry point
ENTRYPOINT ["python", "-m", "image_cli"]
CMD ["--help"]

# Volume declaration for persistent model cache
VOLUME ["/cache"]