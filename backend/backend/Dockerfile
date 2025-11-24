# ===========================
# VENTO AUREO — FINAL DOCKERFILE
# Cloud Run • Python 3.10 • TensorFlow • Prophet
# ===========================

FROM python:3.10-slim

# System dependencies for Prophet + Psycopg2 + TensorFlow
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    libatlas-base-dev \
    liblapack-dev \
    gfortran \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Working directory
WORKDIR /app

# Install Python dependencies
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source
COPY . /app

# Cloud Run environment
ENV PYTHONUNBUFFERED=1
ENV PORT=8080

# Start with Gunicorn
CMD exec gunicorn app:app --bind 0.0.0.0:$PORT --workers 1 --threads 4 --timeout 300
