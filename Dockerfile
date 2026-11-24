# ASD1-M2-14 — Archiwum prac i projektów studenckich Filii
# Minimalny obraz produkcyjny dla Fly.io (i lokalnego `docker build`).

FROM python:3.12-slim

# Konfiguracja środowiska bez pycache'ów i buforów pip (mniejszy obraz).
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HOST=0.0.0.0 \
    PORT=8080

WORKDIR /app

# Najpierw zależności — osobna warstwa cache'uje pip nawet przy zmianach kodu.
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Potem reszta projektu.
COPY server.py ./
COPY src/ ./src/
COPY frontend/ ./frontend/
COPY materialy/ ./materialy/
RUN mkdir -p ./data

# Serwer wiąże się z 0.0.0.0:8080 (porównaj fly.toml internal_port).
EXPOSE 8080

CMD ["python", "server.py"]
