FROM debian:bookworm-slim

# Install dependencies
RUN apt-get update && apt-get install -y \
    curl \
    bash \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install Claude
RUN curl -fsSL https://claude.ai/install.sh | bash

# Set working directory
WORKDIR /app

# Default command
CMD ["bash"]