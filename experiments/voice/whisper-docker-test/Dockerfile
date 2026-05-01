FROM python:3.11-slim

RUN apt-get update
RUN apt-get install -y --no-install-recommends espeak-ng ffmpeg
RUN rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir openai-whisper

WORKDIR /work
ENTRYPOINT ["whisper"]
