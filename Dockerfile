# Use an official Python runtime as a parent image
FROM python:3.13-slim

# Sets the application directory
WORKDIR /app

# Set the PYTHONUNBUFFERED environment variable to ensure output is immediately dumped to the stream
ENV PYTHONUNBUFFERED=1

# Install uv
RUN pip install uv

# Copy only requirements to cache them in Docker layer
COPY pyproject.toml uv.lock* /app/

# Project initialization:
RUN uv sync --frozen --no-dev

# Copies the application code to the Docker image
COPY . /app/

# The command to run the application
CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
