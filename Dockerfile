FROM python:3.11-slim

WORKDIR /app

# Muhit o'zgaruvchilari
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Tizim paketlarini yangilash
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Bog'liqliklarni o'rnatish
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Loyiha kodini ko'chirish
COPY . .

# Papkalarni yaratish
RUN mkdir -p uploads

CMD ["python", "main.py"]
