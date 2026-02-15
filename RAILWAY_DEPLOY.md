# Railway Deployment Guide

This guide explains how to deploy the gpt-oss Responses API server to [Railway](https://railway.app/).

## Prerequisites

- A Railway account ([sign up here](https://railway.app/))
- Access to the gpt-oss model weights (see main [README.md](README.md) for download instructions)
- API keys for optional tools (browser search, etc.)

## Quick Start

1. **Click the Deploy Button** (if available):
   
   [![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/new)

2. **Or manually deploy from your GitHub repository**:
   - Connect your GitHub account to Railway
   - Create a new project and select this repository
   - Railway will automatically detect the configuration files

## Configuration

The deployment is configured through several files:

- **`railway.json`**: Main deployment configuration
- **`nixpacks.toml`**: Build environment and dependencies
- **`runtime.txt`**: Specifies Python 3.12 runtime
- **`Procfile`**: Alternative start command (fallback)
- **`.env.railway.example`**: Template for environment variables (copy and customize)

### Required Environment Variables

Set these environment variables in your Railway project settings. You can use `.env.railway.example` as a template:

| Variable | Description | Example |
|----------|-------------|---------|
| `PORT` | Port for the server (Railway auto-assigns) | `8000` |
| `MODEL_PATH` | Path to model checkpoint | `/app/models/gpt-oss-20b` |
| `INFERENCE_BACKEND` | Inference backend to use | `vllm`, `transformers`, `ollama`, `triton`, or `metal` |

### Optional Environment Variables

For browser tool support:

| Variable | Description | Required For |
|----------|-------------|--------------|
| `BROWSER_BACKEND` | Browser backend (`exa` or `youcom`) | Browser tool |
| `EXA_API_KEY` | Exa API key | Exa browser backend |
| `YDC_API_KEY` | You.com API key | You.com browser backend |

For advanced configurations:

| Variable | Description | Default |
|----------|-------------|---------|
| `TP` | Tensor parallelism size | `2` |
| `PYTORCH_CUDA_ALLOC_CONF` | PyTorch CUDA allocator config | `expandable_segments:True` |

## Model Deployment Options

### Option 1: Using Ollama (Recommended for Railway)

Ollama is the easiest option for Railway deployment as it handles model downloading automatically:

1. Set environment variables:
   ```
   INFERENCE_BACKEND=ollama
   MODEL_PATH=gpt-oss:20b
   ```

2. Ollama will automatically pull the model on first run

### Option 2: Using vLLM or Transformers

For production deployments with GPU support:

1. Set environment variables:
   ```
   INFERENCE_BACKEND=vllm
   MODEL_PATH=openai/gpt-oss-20b
   ```

2. Ensure you have adequate GPU resources (Railway Pro plan recommended)

### Option 3: Pre-uploading Model Weights

For fastest startup times:

1. Upload model weights to a persistent volume or external storage
2. Set `MODEL_PATH` to the mounted volume path
3. Configure Railway to mount the volume to your service

## Deployment Steps

### Deploy from GitHub

1. **Fork or Clone** this repository to your GitHub account

2. **Create a New Railway Project**:
   - Go to [Railway Dashboard](https://railway.app/dashboard)
   - Click "New Project"
   - Select "Deploy from GitHub repo"
   - Choose your forked repository

3. **Configure Environment Variables**:
   - In your Railway project, go to "Variables"
   - Add the required environment variables listed above
   - Railway automatically provides `PORT`

4. **Deploy**:
   - Railway will automatically build and deploy your service
   - Monitor the build logs for any issues
   - Once deployed, Railway will provide a public URL

### Deploy Using Railway CLI

1. **Install Railway CLI**:
   ```bash
   npm i -g @railway/cli
   ```

2. **Login to Railway**:
   ```bash
   railway login
   ```

3. **Initialize Project**:
   ```bash
   railway init
   ```

4. **Add Environment Variables**:
   ```bash
   railway variables set INFERENCE_BACKEND=ollama
   railway variables set MODEL_PATH=gpt-oss:20b
   ```

5. **Deploy**:
   ```bash
   railway up
   ```

## Health Checks

The deployment includes a health check endpoint at `/` that Railway will use to verify the service is running:

- **Path**: `/`
- **Timeout**: 300 seconds (allows time for model loading)
- **Type**: HTTP GET request

## Resource Requirements

Depending on your chosen inference backend:

### gpt-oss-20b
- **Minimum**: 16GB RAM, CPU-only (slow)
- **Recommended**: GPU with 24GB+ VRAM (e.g., NVIDIA RTX 4090, A10G)

### gpt-oss-120b
- **Minimum**: 80GB GPU VRAM (e.g., NVIDIA H100, A100 80GB)
- **Recommended**: Multiple GPUs with tensor parallelism

**Note**: Railway's free tier may not have sufficient resources. A Pro plan with GPU support is recommended for production deployments.

## Monitoring and Logs

- View logs in the Railway dashboard under your service
- Monitor memory and CPU usage in the "Metrics" tab
- Set up alerts for service downtime or errors

## Troubleshooting

### Model Loading Issues

If the service fails to start due to model loading:

1. Increase the health check timeout in `railway.json`
2. Verify `MODEL_PATH` points to the correct location
3. Check logs for specific error messages

### Out of Memory Errors

If you encounter OOM errors:

1. Switch to a smaller model (`gpt-oss-20b` instead of `gpt-oss-120b`)
2. Use quantized versions if available
3. Upgrade to a Railway plan with more resources
4. Consider using Ollama with automatic memory management

### Connection Timeout

If Railway's health check times out:

1. Ensure the server is binding to `0.0.0.0:$PORT`
2. Check that the `PORT` environment variable is properly set
3. Verify no firewall rules are blocking connections

## Cost Optimization

- Use Ollama backend for cost-effective deployment
- Enable auto-scaling based on traffic
- Consider serverless options for intermittent usage
- Monitor resource usage and adjust instance size accordingly

## API Usage

Once deployed, you can use the Responses API:

```bash
curl https://your-railway-app.railway.app/v1/responses \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-oss",
    "messages": [
      {
        "role": "user",
        "content": "What is quantum computing?"
      }
    ]
  }'
```

See the main [README.md](README.md) for more API examples and usage.

## Security Considerations

1. **API Keys**: Never commit API keys to the repository. Use Railway's environment variables.
2. **Access Control**: Consider implementing authentication for production deployments.
3. **Rate Limiting**: Implement rate limiting to prevent abuse.
4. **Network Policies**: Configure Railway's network policies to restrict access if needed.

## Support

For issues specific to:
- **gpt-oss**: See the repository's [issues page](https://github.com/shep95/gpt-oss/issues)
- **Railway**: Check [Railway Documentation](https://docs.railway.app/) or [Railway Discord](https://discord.gg/railway)

## Additional Resources

- [Railway Documentation](https://docs.railway.app/)
- [Nixpacks Documentation](https://nixpacks.com/)
- [gpt-oss Repository](https://github.com/shep95/gpt-oss)
- [Railway Templates](https://railway.app/templates)
