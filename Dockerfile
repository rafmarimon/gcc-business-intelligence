FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libcairo2-dev \
    pkg-config \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install additional dependencies for caching and authentication
RUN pip install --no-cache-dir redis pyjwt

# Copy application code
COPY . .

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=3000 \
    DEBUG=false \
    USE_REDIS_CACHE=true \
    USE_REDIS_AUTH=true

# Expose port
EXPOSE 3000

# Run the application
CMD ["python", "run_api_server.py"] 