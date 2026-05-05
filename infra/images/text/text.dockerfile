FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

RUN apt-get update && \
    apt-get install -y --no-install-recommends build-essential git && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml .
COPY README.md .
COPY src/ src/

RUN uv pip install --system -e ".[api]" torch

ENV NEXUS_TEXT_MODEL_ID=HuggingFaceTB/SmolLM2-135M-Instruct

CMD ["uvicorn", "nexus.text.app:app", "--host", "0.0.0.0", "--port", "8080"]
