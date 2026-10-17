# MitraField: API + render workers + static web app in one Cloud Run service.

# ---- web: static export of the Next.js app
FROM node:22-slim AS web
WORKDIR /web
COPY web/package.json web/package-lock.json ./
RUN npm ci
COPY web/ ./
RUN NODE_ENV=production npx next build

# ---- runtime: Python + ffmpeg + cairo/pango + LaTeX for Manim
FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
      ffmpeg libcairo2-dev libpango1.0-dev pkg-config build-essential \
      texlive-latex-base texlive-latex-recommended texlive-latex-extra texlive-fonts-recommended texlive-science dvisvgm \
      fontconfig \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY assets/fonts/ /usr/share/fonts/truetype/mitrafield/
RUN fc-cache -f
COPY backend/ backend/
COPY assets/ assets/
COPY cli.py .
COPY --from=web /web/out web/out

# On Cloud Run: Vertex AI via the service account, projects on a Cloud Storage mount,
# no local GPU voice server (narration uses Gemini TTS).
ENV STUDIO_MANIM_PY=python STUDIO_OMNI_URL="" STUDIO_DATA=/data/projects PORT=8080
CMD ["sh", "-c", "exec uvicorn backend.app:app --host 0.0.0.0 --port ${PORT}"]
