FROM python:3.11-slim

# Install system dependencies: Tesseract OCR, LibreOffice headless, poppler-utils
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-eng \
    libreoffice-writer \
    libreoffice-calc \
    poppler-utils \
    libgl1 \
    libglib2.0-0 \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY . .

# Ensure data directory exists
RUN mkdir -p /app/data/uploads /app/data/thumbnails /app/data/logs /app/data/chroma

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
