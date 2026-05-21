FROM python:3.12-slim

# Install system dependencies including Tesseract OCR
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-eng \
    libtesseract-dev \
    libpq-dev \
    gcc \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Railway (and others) set PORT; default 8000 for local runs
ENV PORT=8000
EXPOSE 8000

# Start gunicorn (shell form so $PORT is expanded).
# Long timeout for OCR/PDF-heavy routes; tune with GUNICORN_TIMEOUT on the host if needed.
# max-requests recycles workers to reduce memory growth on small instances.
CMD gunicorn app:app --bind 0.0.0.0:${PORT} --workers 2 --timeout ${GUNICORN_TIMEOUT:-600} --graceful-timeout 120 --max-requests 2000 --max-requests-jitter 200
