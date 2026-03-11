FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# Use Uvicorn directly since SSE requires highly concurrent async task handling
# Gunicorn can buffer SSE events which ruins real-time tracking
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
