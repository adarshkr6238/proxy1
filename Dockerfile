FROM python:3.11-slim

# Install FFmpeg and build dependencies for tgcrypto
RUN apt-get update && apt-get install -y \
    ffmpeg \
    gcc \
    python3-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Remove build dependencies to keep image small
RUN apt-get purge -y --auto-remove gcc python3-dev libssl-dev

COPY . .

# Ensure tmp directories exist
RUN mkdir -p /tmp/bot_downloads /tmp/bot_temp

CMD ["python", "main.py"]
