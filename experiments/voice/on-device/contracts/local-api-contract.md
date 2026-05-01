# Local API Contract

This contract is internal and local to the app process. It mirrors the shape of the lab API while remaining on-device-only.

## Health

### Request

`HealthCheckRequest`

### Response

`HealthCheckResponse`

```json
{
  "ok": true,
  "active_backend": "coreml",
  "available_tasks": ["tts", "stt"]
}
```

## Text to speech

### Request

```json
{
  "text": "Hello from Nexus Voice.",
  "voice": "default.en.us.female",
  "locale": "en-US"
}
```

### Response

```json
{
  "output_file_url": "file:///local/path/to/audio.wav",
  "sample_rate_hz": 24000,
  "duration_ms": 2150
}
```

## Speech to text

### Request

```json
{
  "audio_file_url": "file:///local/path/to/input.wav",
  "locale": "en-US"
}
```

### Response

```json
{
  "text": "Hello from Nexus Voice.",
  "duration_ms": 2140
}
```

## Error envelope

```json
{
  "error": {
    "code": "MODEL_PACK_MISSING",
    "message": "No active model pack for task tts.",
    "details": "Install a TTS model pack in settings."
  }
}
```

## Error codes

- `INVALID_REQUEST`
- `MODEL_PACK_MISSING`
- `MODEL_PACK_CORRUPT`
- `BACKEND_UNAVAILABLE`
- `INFERENCE_FAILED`
- `UNSUPPORTED_LOCALE`

