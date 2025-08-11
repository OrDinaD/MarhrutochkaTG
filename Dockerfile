# Use the Python 3 official image optimized for Railway
# https://hub.docker.com/_/python
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Set environment variables for Railway deployment
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
ENV PIP_NO_CACHE_DIR=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies required for bot functionality
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy requirements first for better Docker layer caching
COPY requirements.txt ./

# Install Python dependencies with optimizations
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . ./

# Create necessary directories for logging and data storage
RUN mkdir -p data/logs data/crash_logs data/user_sessions \
    && touch data/logs/bot.log

# Create a non-privileged user for security
RUN useradd --create-home --shell /bin/bash --user-group railway \
    && chown -R railway:railway /app

# Switch to non-privileged user
USER railway

# Health check endpoint for Railway monitoring
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "import sys; sys.exit(0)" || exit 1

# Railway will automatically set the PORT environment variable
# The bot will adapt to Railway's environment automatically

# Start the bot with crash handling
CMD ["python", "main.py"]
