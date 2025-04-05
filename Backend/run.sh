#!/bin/bash
# Backend/run.sh
# Skript zum Starten des Backends

# Virtuelle Umgebung aktivieren, falls vorhanden
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Umgebungsvariablen aus .env laden
export $(grep -v '^#' .env | xargs)

# Flask-App starten
flask run --host=0.0.0.0 --port=$PORT