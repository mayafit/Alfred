FROM python:3.11-slim

WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

COPY app.py .
RUN pip install --no-cache-dir flask requests

EXPOSE 9001
CMD ["python", "app.py"]
