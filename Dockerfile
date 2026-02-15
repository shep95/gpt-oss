# Use NVIDIA CUDA base image for GPU support
FROM nvidia/cuda:12.1.1-devel-ubuntu22.04

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3.12 \
    python3-pip \
    git \
    wget \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip
RUN pip3 install --upgrade pip

# Copy project files
COPY pyproject.toml ./
COPY gpt_oss ./gpt_oss
COPY _build ./_build
COPY CMakeLists.txt ./
COPY MANIFEST.in ./

# Install Python dependencies
RUN pip3 install -e .

# Install vLLM for inference (Railway deployment recommended backend)
RUN pip3 install --pre vllm==0.10.1+gptoss \
    --extra-index-url https://wheels.vllm.ai/gpt-oss/ \
    --extra-index-url https://download.pytorch.org/whl/nightly/cu128 \
    --index-strategy unsafe-best-match

# Expose port (Railway will set $PORT environment variable)
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=300s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8000}/health || exit 1

# Start the server
CMD python3 -m gpt_oss.responses_api.serve --inference-backend ${INFERENCE_BACKEND:-vllm} --port ${PORT:-8000} --checkpoint ${MODEL_CHECKPOINT:-~/model}
