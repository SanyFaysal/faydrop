FROM python:3.11-slim

# Install system ffmpeg, nodejs and certificates
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    nodejs \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Default port (Hugging Face Spaces uses 7860, Render uses $PORT)
ENV PORT=7860
ENV PYTHONUNBUFFERED=1

EXPOSE 7860

# Start Faydrop application
CMD ["python", "main.py", "--no-browser"]

