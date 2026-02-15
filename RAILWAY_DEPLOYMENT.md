# Railway Deployment Guide for gpt-oss

This guide provides detailed instructions for deploying gpt-oss on Railway.

## Overview

Railway is a deployment platform that provides GPU-enabled infrastructure, making it suitable for running large language models like gpt-oss. This repository includes pre-configured files for Railway deployment:

- `railway.toml` - Railway service configuration
- `Dockerfile` - Container definition with CUDA support
- `.dockerignore` - Optimizes Docker build by excluding unnecessary files

## Prerequisites

1. **Railway Account**: Sign up at [railway.app](https://railway.app)
2. **GPU Access**: Ensure your Railway plan includes GPU instances
3. **Model Weights**: Plan how you'll provide model weights to your deployment

## Deployment Steps

### 1. Prepare Your Repository

Fork or clone this repository to your GitHub account:

```bash
git clone https://github.com/openai/gpt-oss.git
cd gpt-oss
```

### 2. Create a Railway Project

1. Go to [railway.app](https://railway.app) and log in
2. Click "New Project"
3. Select "Deploy from GitHub repo"
4. Choose your forked gpt-oss repository
5. Railway will automatically detect the `railway.toml` and `Dockerfile`

### 3. Configure Environment Variables

In your Railway project settings, add the following environment variables:

#### Required Variables

- `INFERENCE_BACKEND` - The inference backend to use
  - Options: `vllm` (recommended), `transformers`, `ollama`
  - Example: `vllm`

- `MODEL_CHECKPOINT` - Path to model weights
  - For Railway volumes: `/app/model/gpt-oss-20b`
  - For HuggingFace: `openai/gpt-oss-20b`

#### Optional Variables

- `BROWSER_BACKEND` - Browser tool backend (if using browser tools)
  - Options: `exa`, `youcom`
  - Default: `exa`

- `YDC_API_KEY` - API key for You.com browser backend
  - Required only if `BROWSER_BACKEND=youcom`

- `EXA_API_KEY` - API key for Exa browser backend
  - Required only if `BROWSER_BACKEND=exa`

- `PORT` - Server port (Railway sets this automatically)
  - Default: `8000`

### 4. Set Up Model Storage

Since model weights are too large for the Docker image, choose one of these options:

#### Option A: Railway Volumes (Recommended)

1. In Railway, add a volume to your service
2. Mount it to `/app/model`
3. Use Railway's shell to download models:

```bash
# Connect to your Railway service shell
pip install huggingface_hub
python -c "from huggingface_hub import snapshot_download; snapshot_download('openai/gpt-oss-20b', local_dir='/app/model/gpt-oss-20b')"
```

4. Set `MODEL_CHECKPOINT=/app/model/gpt-oss-20b`

#### Option B: Direct HuggingFace Download

Set `MODEL_CHECKPOINT=openai/gpt-oss-20b` and the model will be downloaded on first use. Note that this will increase startup time significantly.

#### Option C: External Storage

Store models in S3, Google Cloud Storage, or similar:

1. Add download logic to your startup script
2. Use environment variables for storage credentials
3. Download models to `/app/model` on container start

### 5. Deploy

1. Click "Deploy" in Railway
2. Railway will build your Docker image (this takes 10-15 minutes the first time)
3. Once deployed, your service will be available at the Railway-provided URL
4. Access the API at `https://your-app.railway.app/v1/responses`

## Verification

### Health Check

Railway automatically monitors the `/health` endpoint:

```bash
curl https://your-app.railway.app/health
# Expected response: {"status": "healthy"}
```

### Test Inference

Send a test request to verify the API is working:

```bash
curl -X POST https://your-app.railway.app/v1/responses \
  -H "Content-Type: application/json" \
  -d '{
    "conversation": [
      {
        "role": "user",
        "content": "Say hello!"
      }
    ],
    "stream": false
  }'
```

## Troubleshooting

### Build Failures

- **Out of Memory**: Reduce build parallelism or increase memory allocation
- **CUDA Issues**: Ensure you're using GPU-enabled Railway instances
- **Dependency Conflicts**: Check `pyproject.toml` versions match your environment

### Runtime Issues

- **Model Not Found**: Verify `MODEL_CHECKPOINT` path and volume mount
- **Out of Memory**: Use a smaller model (`gpt-oss-20b` instead of `gpt-oss-120b`) or increase GPU memory
- **Slow Responses**: Ensure you're using `vllm` backend for optimal performance

### Logs

View logs in Railway dashboard:
1. Open your project
2. Click on your service
3. Select "Logs" tab
4. Look for startup messages and errors

## Performance Optimization

### Model Selection

- **gpt-oss-20b**: Requires ~16GB memory, faster inference
- **gpt-oss-120b**: Requires ~80GB memory, higher quality

### Inference Backend

- **vllm** (Recommended): Best performance, GPU-optimized
- **transformers**: Simpler but slower
- **ollama**: Good for testing, requires separate Ollama service

### Scaling

Railway supports:
- Vertical scaling: Increase CPU/GPU/memory
- Horizontal scaling: Multiple replicas (requires load balancer configuration)

## Cost Considerations

- GPU instances are more expensive than CPU-only
- Model storage in volumes incurs storage costs
- Consider using smaller models for development/testing
- Scale down or pause deployments when not in use

## Security

- Keep API keys secure using Railway's environment variables
- Never commit secrets to your repository
- Use Railway's private networking for internal services
- Consider adding authentication to your API endpoints

## Additional Resources

- [Railway Documentation](https://docs.railway.app)
- [gpt-oss Repository](https://github.com/openai/gpt-oss)
- [vLLM Documentation](https://docs.vllm.ai)
- [Harmony Format Guide](https://cookbook.openai.com/articles/openai-harmony)

## Support

For Railway-specific issues:
- Railway Discord: [discord.gg/railway](https://discord.gg/railway)
- Railway Docs: [docs.railway.app](https://docs.railway.app)

For gpt-oss issues:
- GitHub Issues: [github.com/openai/gpt-oss/issues](https://github.com/openai/gpt-oss/issues)
