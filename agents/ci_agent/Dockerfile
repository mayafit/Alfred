FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

# Create directory for templates and repo storage
RUN mkdir -p /app/templates /tmp/repos

COPY app.py repo_analyzer.py ./
COPY templates/*.groovy templates/
RUN pip install --no-cache-dir flask requests

EXPOSE 9001
CMD ["python", "app.py"]