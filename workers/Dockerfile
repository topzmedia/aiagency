FROM python:3.11-slim

# System dependencies (same as API for shared ML/media processing)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY workers/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy workers code AND apps/api code (workers import from apps.api.services)
COPY workers/ /app/workers/
COPY apps/ /app/apps/
COPY scripts/ /app/scripts/
COPY data/ /app/data/

ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

CMD ["celery", "-A", "workers.celery_app", "worker", "-l", "info"]
