# gpt-oss Responses API server — Railway deployment image
#
# Builds a single, deterministic environment so runtime dependencies
# (uvicorn, fastapi, ...) are guaranteed to be importable. This avoids the
# Railway build-vs-runtime environment split that produced
# "ModuleNotFoundError: No module named 'uvicorn'".
#
# Defaults to the `stub` inference backend, which needs no GPU, no torch and
# no model weights — the only backend that can boot on a standard Railway
# container. Override INFERENCE_BACKEND (and provide weights + a GPU) to run a
# real model.

FROM python:3.12-slim

WORKDIR /app

# Copy the full source tree (the custom PEP 517 build backend lives in _build/
# and must be importable during `pip install .`).
COPY . .

# Pure-wheel install (GPTOSS_BUILD_METAL unset -> setuptools backend, no CMake).
RUN python -m pip install --upgrade pip \
    && python -m pip install .

# stub = CPU-only, no weights. Boots the API and returns canned tokens.
ENV INFERENCE_BACKEND=stub
ENV PORT=8000

EXPOSE 8000

CMD ["python", "-m", "gpt_oss.responses_api.serve"]
