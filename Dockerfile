FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
COPY src ./src

RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir .

EXPOSE 8787

CMD ["python", "-m", "uvicorn", "nexus.api.app:app", "--host", "0.0.0.0", "--port", "8787"]
