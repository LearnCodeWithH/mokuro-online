# Build stage - uses Poetry to manage dependencies
FROM python:3.10-slim AS builder

ENV POETRY_HOME="/opt/poetry" \
    POETRY_VERSION=1.6.1 \
    POETRY_NO_INTERACTION=1 \
    POETRY_VENV_IN_PROJECT=1 \
    POETRY_CACHE_DIR=/tmp/poetry_cache

# Install poetry and build dependencies
RUN apt-get update && \
    apt-get install -y curl && \
    curl -sSL https://install.python-poetry.org | python3 - && \
    ln -s $POETRY_HOME/bin/poetry /usr/local/bin/poetry

WORKDIR /app

# Copy poetry files
COPY pyproject.toml poetry.lock ./

# Add gunicorn and export dependencies to requirements.txt
RUN poetry add gunicorn@^23.0.0 && \
    poetry export -f requirements.txt --output requirements.txt --without dev

# Runtime stage - minimal image with only necessary dependencies
FROM nvidia/cuda:12.6.3-base-ubuntu22.04

ENV PYTHONUNBUFFERED=1 \
    APP_PORT=8000 \
    PYTHONDONTWRITEBYTECODE=1

# Install Python and shared dependencies for GPU support
RUN apt-get update && \
    apt-get install -y python3 python3-pip libgl1 libglib2.0-0 && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Create symbolic link for python command
RUN ln -s /usr/bin/python3 /usr/bin/python

WORKDIR /app

# Copy requirements from build stage and install dependencies
COPY --from=builder /app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Mask SECRET_KEY from docker output
RUN python3 populate_secret.py

EXPOSE $APP_PORT
CMD gunicorn --bind 0.0.0.0:$APP_PORT "app:create_app('production')"