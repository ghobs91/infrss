# Use an official Python runtime as a parent image
# Pinned to the patch tag that ":3.12-slim" currently resolves to. A floating tag rebuilds the base
# layer whenever Python/Debian publish, which drops every cached layer below it.
FROM python:3.12.16-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# No apt layer: the slim image already ships ca-certificates (the previous
# `apt-get update && install ca-certificates` was a pure network round trip), and every pin in
# requirements.txt resolves to a prebuilt wheel, so no compiler is needed.

# Set working directory
WORKDIR /app

# Copy requirements file
COPY requirements.txt .

# gitignore-parser ships no wheel, so pip builds it from source. By default that
# spins up an isolated build env and re-fetches setuptools/wheel from PyPI even
# though they're already installed below — an extra network round trip that has
# caused self-hosted builds to fail on flaky/restricted DNS. Install the build
# tools first and build it with --no-build-isolation to skip that fetch.
#
# The pip cache mount replaces --no-cache-dir: wheels downloaded once survive a retried or
# invalidated build instead of being pulled down again. A mount is not an image layer, so the
# image size is unchanged.
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --upgrade pip setuptools wheel \
    && pip install --no-build-isolation gitignore-parser==0.1.13

# Install Python dependencies
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt

# Copy the alembic configuration first
COPY alembic.ini .

# Copy the application code
COPY ./alembic ./alembic
COPY ./app ./app
COPY ./scripts ./scripts

# Expose the port the app runs on
EXPOSE 8008

# Command to run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8008"]
