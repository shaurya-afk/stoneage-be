# Python 3.11 (Render / spaCy compatibility)
FROM python:3.11-slim

WORKDIR /app

# Ensure Python output is flushed immediately (critical for Render logs)
ENV PYTHONUNBUFFERED=1

# Install Tesseract OCR and poppler (required by pdf2image for PDF → image conversion)
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-eng \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Render sets PORT; default 8000 for local Docker
EXPOSE 8000
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --log-level info
