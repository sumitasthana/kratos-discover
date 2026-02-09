# Use Python 3.9 slim image as base
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create directories for data and outputs
RUN mkdir -p /app/data /app/outputs /app/config

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app:${PATH}"

# Create non-root user for security
RUN useradd -m -u 1000 kratos && \
    chown -R kratos:kratos /app
USER kratos

# Default command - can be overridden
ENTRYPOINT ["python", "cli.py"]
CMD ["--help"]
