# Use Python 3.11 slim image as base
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create a virtual environment in /venv
RUN python -m venv /venv
# Update PATH so that the virtual environment's executables are used
ENV PATH="/venv/bin:$PATH"

# Copy application code
COPY . .

# Install Python dependencies inside the venv
RUN pip install --no-cache-dir \
    flask \
    flask-sqlalchemy \
    gunicorn \
    jira \
    openai \
    requests \
    psycopg2-binary \
    prometheus-flask-exporter \
    prometheus-client

# Set environment variables
ENV FLASK_APP=app.py
ENV PYTHONUNBUFFERED=1
ENV PORT=5000
ENV PYTHONPATH=/app

# Make start script executable
RUN chmod +x start.sh

# Expose port
EXPOSE 5000

# Use the startup script
CMD ["./start.sh", "gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "main:app"]