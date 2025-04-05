#!/bin/bash
# Backend/setup.sh
# Skript zur Einrichtung des Backends

# Virtuelle Umgebung erstellen
python -m venv venv

# Virtuelle Umgebung aktivieren
source venv/bin/activate

# Abhängigkeiten installieren
pip install -r requirements.txt

# SpaCy-Sprachmodelle installieren
python -m spacy download de_core_news_sm
python -m spacy download en_core_web_sm

# Verzeichnisse erstellen
mkdir -p uploads
mkdir -p data/chroma

# Ausführungsrechte für run.sh setzen
chmod +x run.sh

echo "Setup abgeschlossen. Starten Sie das Backend mit ./run.sh"