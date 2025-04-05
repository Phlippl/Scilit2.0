# Backend/Dockerfile
FROM python:3.10-slim

# Tesseract OCR und weitere Abhängigkeiten installieren
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    libtesseract-dev \
    ffmpeg \
    libsm6 \
    libxext6 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Abhängigkeiten zuerst kopieren und installieren (besseres Caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# SpaCy-Sprachmodelle installieren
RUN python -m spacy download de_core_news_sm
RUN python -m spacy download en_core_web_sm

# Restliche Dateien kopieren
COPY . .

# Verzeichnisse erstellen
RUN mkdir -p uploads data/chroma

# Port freigeben
EXPOSE 5000

# Umgebungsvariablen
ENV FLASK_APP=app.py
ENV PORT=5000

# Container starten
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:create_app()"]