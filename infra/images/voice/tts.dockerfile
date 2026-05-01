FROM python:3.11-slim

RUN apt-get update
RUN apt-get install -y --no-install-recommends espeak-ng
RUN rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir "kokoro>=0.9.2" soundfile

WORKDIR /work
CMD ["python", "generate.py"]
