FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY service-auth/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy shared models and DB configuration
COPY shared /app/shared

# Copy the specific microservice
COPY service-auth /app/service-auth

# Set working directory to the microservice itself so imports work seamlessly
WORKDIR /app/service-auth
ENV PYTHONPATH=/app

EXPOSE 8000

# Production Optimization: Run with Gunicorn Uvicorn workers
CMD ["gunicorn", "main:app", "-w", "1", "-k", "uvicorn.workers.UvicornWorker", "-b", "0.0.0.0:8000"]
