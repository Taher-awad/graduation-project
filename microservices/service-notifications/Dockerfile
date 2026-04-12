FROM python:3.11-slim

WORKDIR /app

COPY service-notifications/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy shared models and configuration
COPY shared /app/shared

# Copy the specific microservice
COPY service-notifications /app/service-notifications

WORKDIR /app/service-notifications
ENV PYTHONPATH=/app

EXPOSE 8000

# Use Uvicorn directly since SSE requires highly concurrent async task handling
# Gunicorn can buffer SSE events which ruins real-time tracking
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
