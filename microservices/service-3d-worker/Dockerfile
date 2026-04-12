FROM python:3.10-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    blender \
    python3-numpy \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY service-3d-worker/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy shared models
COPY shared /app/shared

# Copy worker files
COPY service-3d-worker /app/service-3d-worker

WORKDIR /app/service-3d-worker
ENV PYTHONPATH=/app

# Environment Variables
ENV CELERY_BROKER_URL=redis://redis:6379/0
ENV CELERY_RESULT_BACKEND=redis://redis:6379/0

# CMD set in docker-compose
