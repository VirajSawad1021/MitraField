# MitraField: one image, two Cloud Run services (STUDIO_ROLE=api serves the UI and API,
# STUDIO_ROLE=worker runs render jobs). Built by Cloud Build; see docs/ARCHITECTURE.md.

# ---- web: static export of the Next.js app
FROM node:22-slim AS web
WORKDIR /web
COPY web/package.json web/package-lock.json ./
RUN npm ci
COPY web/ ./
RUN NODE_ENV=production npx next build

# ---- runtime: Python + ffmpeg + cairo/pango + LaTeX for Manim + Chromium for motion scenes
FROM python:3.14-slim
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 DEBIAN_FRONTEND=noninteractive \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
RUN apt-get update && apt-get install -y --no-install-recommends \
      ffmpeg libcairo2-dev libpango1.0-dev pkg-config build-essential \
      texlive-latex-base texlive-latex-recommended texlive-latex-extra texlive-fonts-recommended texlive-science dvisvgm \
      fontconfig curl util-linux \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt && playwright install --with-deps chromium && rm -rf /var/lib/apt/lists/*
COPY assets/fonts/ /usr/share/fonts/truetype/mitrafield/
COPY deploy/fetch_fonts.sh /tmp/fetch_fonts.sh
RUN bash /tmp/fetch_fonts.sh /usr/share/fonts/truetype/noto-mitrafield && fc-cache -f
COPY backend/ backend/
COPY assets/ assets/
COPY cli.py .
COPY --from=web /web/out web/out

# Run as an unprivileged user. The Cloud Storage volume is mounted with this uid (see deploy/deploy.sh).
RUN useradd --uid 10001 --create-home app && chown -R app /app
USER app

# The image holds no API key: Cloud Run injects it from Secret Manager (or Vertex AI uses the service
# account, STUDIO_VERTEX=1). Projects live in Firestore; media on a Cloud Storage mount; jobs go through Cloud Tasks.
ENV STUDIO_MANIM_PY=python STUDIO_OMNI_URL="" STUDIO_DATA=/data/projects PORT=8080 \
    STUDIO_STORE=firestore STUDIO_QUEUE=cloudtasks
CMD ["sh", "-c", "exec uvicorn backend.app:app --host 0.0.0.0 --port ${PORT} --proxy-headers --forwarded-allow-ips='*'"]
