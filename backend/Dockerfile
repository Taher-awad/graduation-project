FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
# libxi6, libxrender1, etc are needed for Blender
RUN apt-get update && apt-get install -y \
    wget \
    xz-utils \
    libxi6 \
    libxrender1 \
    libxxf86vm1 \
    libxfixes3 \
    libxcursor1 \
    libgl1 \
    libdbus-1-3 \
    libx11-6 \
    libxkbcommon0 \
    libsm6 \
    libice6 \
    libxext6 \
    && rm -rf /var/lib/apt/lists/*

# Install Blender (Downloading binary for control over version, e.g., 3.6 LTS)
# Using 3.6 LTS as it is stable and widely supported
RUN wget https://download.blender.org/release/Blender3.6/blender-3.6.4-linux-x64.tar.xz \
    && tar -xf blender-3.6.4-linux-x64.tar.xz \
    && mv blender-3.6.4-linux-x64 /usr/local/blender \
    && rm blender-3.6.4-linux-x64.tar.xz \
    && ln -s /usr/local/blender/blender /usr/local/bin/blender

# Install gltfpack (Updated to v0.25)
RUN apt-get update && apt-get install -y unzip \
    && wget https://github.com/zeux/meshoptimizer/releases/download/v0.25/gltfpack-ubuntu.zip \
    && unzip gltfpack-ubuntu.zip \
    && mv gltfpack /usr/local/bin/ \
    && chmod +x /usr/local/bin/gltfpack \
    && rm gltfpack-ubuntu.zip

# Python Dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy App Code
COPY . .

# Default command (overridden in docker-compose)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
