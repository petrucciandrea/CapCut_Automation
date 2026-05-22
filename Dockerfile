# Usa un'immagine Python ufficiale e leggera basata su Debian
FROM python:3.10-slim

# Imposta la cartella di lavoro all'interno del container
WORKDIR /app

# Installa FFmpeg e Git a livello di sistema operativo Linux
RUN apt-get update && apt-get install -y \
    ffmpeg \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copia il file dei requisiti e installa le librerie Python con timeout esteso
COPY requirements.txt .
RUN pip install --default-timeout=100 --no-cache-dir -r requirements.txt

# Il container rimarrà attivo in ascolto dei nostri comandi interattivi
CMD ["python", "src/main.py"]