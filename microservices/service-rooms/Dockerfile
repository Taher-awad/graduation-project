FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY service-rooms/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy shared models and DB configuration
COPY shared /app/shared

# Copy the specific microservice
COPY service-rooms /app/service-rooms

# Install shared module
RUN pip install -e /app/shared

# Set working directory to the microservice itself so imports work seamlessly
WORKDIR /app/service-rooms
ENV PYTHONPATH=/app

EXPOSE 8000

# Production Optimization: Run with Gunicorn Uvicorn workers
CMD ["gunicorn", "main:app", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "-b", "0.0.0.0:8000"]
