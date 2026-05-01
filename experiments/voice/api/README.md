# Nexus Voice API

Small FastAPI wrapper around the local voice experiments.

## Preferred workflow

From `~/Developer/nexus/experiments/voice`:

```sh
just lab-up
```

```sh
just api
```

`lab-up` starts the API inside Docker Compose. `api` starts it directly on host.

## Start

```sh
cd ~/Developer/nexus/experiments/voice/api
./run.sh
```

The server listens on `http://127.0.0.1:8787`.
Use `UVICORN_HOST=0.0.0.0` if you need external/container access.

The Kokoro and Whisper endpoints use Docker images and will build them on first
request if they are missing. The VibeVoice endpoint uses the local VibeVoice
`uv` environment because that path can use Apple MPS.

The Compose setup mounts the Docker socket into the API container so the API can
start model containers. This is convenient for local experiments and should be
treated as a trusted-dev-only setup.

## Endpoints

```sh
curl http://127.0.0.1:8787/health
```

```sh
curl -X POST http://127.0.0.1:8787/tts/kokoro \
  -H "Content-Type: application/json" \
  -d '{"text":"Hello from Kokoro through the Nexus voice API."}' \
  --output kokoro.wav
```

```sh
curl -X POST http://127.0.0.1:8787/tts/vibevoice \
  -H "Content-Type: application/json" \
  -d '{"text":"Hello from Microsoft VibeVoice through the Nexus voice API.","speaker":"Carter"}' \
  --output vibevoice.wav
```

```sh
curl -X POST http://127.0.0.1:8787/transcribe \
  -F "audio=@kokoro.wav"
```
