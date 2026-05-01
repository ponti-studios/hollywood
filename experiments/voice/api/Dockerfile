FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

RUN apt-get update
RUN apt-get install -y --no-install-recommends docker.io git
RUN rm -rf /var/lib/apt/lists/*

WORKDIR /Users/charlesponti/Developer/nexus/experiments/voice/api

CMD ["./run.sh"]
