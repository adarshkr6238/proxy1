FROM python:3.11-slim

# Install FFmpeg
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Ensure tmp directories exist
RUN mkdir -p /tmp/bot_downloads /tmp/bot_temp

CMD ["python", "main.py"]
