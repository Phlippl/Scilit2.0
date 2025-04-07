# Backend/Dockerfile
FROM python:3.10-slim

# Install Tesseract OCR and additional dependencies
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-deu \
    tesseract-ocr-eng \
    libtesseract-dev \
    ffmpeg \
    libsm6 \
    libxext6 \
    curl \
    poppler-utils \
    build-essential \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install spaCy language models
# Note: We now install these via requirements.txt which is more reliable
# but keep this as a fallback
RUN if ! python -c "import spacy; spacy.load('de_core_news_sm')" 2>/dev/null; then \
    python -m spacy download de_core_news_sm; \
    fi
RUN if ! python -c "import spacy; spacy.load('en_core_web_sm')" 2>/dev/null; then \
    python -m spacy download en_core_web_sm; \
    fi

# Copy the rest of the files
COPY . .

# Create directories
RUN mkdir -p uploads data/chroma

# Expose port
EXPOSE 5000

# Environment variables
ENV FLASK_APP=app.py
ENV PORT=5000
ENV PYTHONUNBUFFERED=1

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
  CMD curl -f http://localhost:5000/ || exit 1

# Set user for security
RUN useradd -m appuser
RUN chown -R appuser:appuser /app
USER appuser

# Start container
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "--timeout", "120", "app:create_app()"]