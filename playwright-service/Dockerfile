FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl wget gnupg \
    && pip install --no-cache-dir playwright fastapi uvicorn httpx \
    && playwright install chromium \
    && playwright install-deps chromium \
    && rm -rf /var/lib/apt/lists/*

COPY server.py .

EXPOSE 3001

CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "3001"]
