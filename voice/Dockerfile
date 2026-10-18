# OmniVoice on a Cloud Run GPU (NVIDIA L4). The CUDA runtime ships inside the torch wheels; Cloud Run supplies the driver.
FROM python:3.11-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_DISABLE_PIP_VERSION_CHECK=1 HF_HOME=/opt/hf
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg libsndfile1 libgomp1 \
 && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# Weights in the image: no download at cold start.
RUN python -c "from huggingface_hub import snapshot_download as d; d('k2-fsa/OmniVoice')"
COPY server.py .
RUN useradd --uid 10001 --create-home app && chmod -R a+rX /opt/hf
USER app
ENV HF_HUB_OFFLINE=1 PORT=8080
CMD ["sh", "-c", "exec uvicorn server:app --host 0.0.0.0 --port ${PORT} --workers 1 --timeout-graceful-shutdown 30"]
