FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --no-cache-dir --break-system-packages -r requirements.txt

COPY . .

RUN mkdir -p /var/log/analytics

EXPOSE 8050

ENV PYTHONUNBUFFERED=1

CMD ["gunicorn", "main:server", "-c", "gunicorn.conf.py"]
