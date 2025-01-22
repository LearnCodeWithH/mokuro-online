FROM nvidia/cuda:12.6.3-base-ubuntu22.04
FROM python:3.10-slim

ENV PYTHONUNBUFFERED=1 \
    POETRY_HOME="/opt/poetry" \
    POETRY_VERSION=1.6.1 \
    APP_PORT=8000

# Install shared dependencies for gpu support
RUN apt-get update && \
    apt-get install -y curl libgl1 libglib2.0-0

# Install poetry
RUN curl -sSL https://install.python-poetry.org | python3 - && \
    ln -s $POETRY_HOME/bin/poetry /usr/local/bin/poetry

# Cleanup apt-get
RUN apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml poetry.lock ./
RUN poetry add gunicorn@^23.0.0
RUN poetry install --no-root --without dev

COPY . .

# Mask SECRET_KEY from docker output
RUN python3 populate_secret.py

EXPOSE $APP_PORT
CMD poetry run gunicorn --bind 0.0.0.0:$APP_PORT "app:create_app('production')"