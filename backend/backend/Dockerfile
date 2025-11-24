# Dockerfile (for Cloud Run)
FROM python:3.10-slim

# System deps for psycopg2 and prophet + building wheels (prophet may need a compiler)
RUN apt-get update && apt-get install -y build-essential libpq-dev curl git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements to build
COPY backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy application
COPY backend /app

ENV PYTHONUNBUFFERED=1
ENV PORT=8080

CMD exec gunicorn app:app --bind 0.0.0.0:$PORT --workers 2 --threads 2
