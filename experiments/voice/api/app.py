from __future__ import annotations

import asyncio
import shutil
import subprocess
import uuid
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field


ROOT = Path(__file__).resolve().parents[1]
TTS_ROOT = ROOT / "tts-model-comparison"
KOKORO_ROOT = TTS_ROOT / "kokoro"
VIBEVOICE_ROOT = TTS_ROOT / "vibevoice"
WHISPER_ROOT = ROOT / "whisper-docker-test"
RUNTIME_ROOT = ROOT / "api" / "runtime"

app = FastAPI(title="Nexus Voice Experiments API", version="0.1.0")


class ApiError(BaseModel):
    code: str
    message: str
    details: str | None = None


class TtsRequest(BaseModel):
    text: str = Field(min_length=1, max_length=2000)


class KokoroRequest(TtsRequest):
    voice: str = Field(default="af_heart", min_length=1, max_length=80)
    lang_code: str = Field(default="a", min_length=1, max_length=8)


class VibeVoiceRequest(TtsRequest):
    speaker: str = Field(default="Carter", min_length=1, max_length=80)


def error_response(status_code: int, code: str, message: str, details: str | None = None) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail=ApiError(code=code, message=message, details=details).model_dump(),
    )


def run_command(command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=cwd, text=True, capture_output=True, check=False)


async def run_checked(command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    result = await asyncio.to_thread(run_command, command, cwd)
    if result.returncode != 0:
        raise error_response(
            500,
            "RUNNER_FAILED",
            "The model runner failed.",
            (result.stderr or result.stdout)[-4000:],
        )
    return result


async def ensure_docker_image(image: str, context: Path) -> None:
    result = await asyncio.to_thread(run_command, ["docker", "image", "inspect", image], context)
    if result.returncode == 0:
        return

    await run_checked(["docker", "build", "-t", image, "."], context)


def make_run_dir(prefix: str) -> Path:
    run_dir = RUNTIME_ROOT / f"{prefix}-{uuid.uuid4().hex}"
    run_dir.mkdir(parents=True, exist_ok=False)
    return run_dir


@app.get("/health")
def health() -> dict[str, object]:
    return {
        "data": {
            "ok": True,
            "kokoro_image": "nexus-kokoro-tts",
            "whisper_image": "whisper-docker-smoke",
            "vibevoice": VIBEVOICE_ROOT.exists(),
        }
    }


@app.post("/tts/kokoro", response_class=FileResponse)
async def kokoro_tts(request: KokoroRequest) -> FileResponse:
    run_dir = make_run_dir("kokoro")
    text_file = run_dir / "input.txt"
    output_file = run_dir / "kokoro.wav"
    text_file.write_text(request.text, encoding="utf-8")

    await ensure_docker_image("nexus-kokoro-tts", KOKORO_ROOT)
    await run_checked(
        [
            "docker",
            "run",
            "--rm",
            "-v",
            f"{KOKORO_ROOT}:/work",
            "-v",
            f"{KOKORO_ROOT / '.cache'}:/root/.cache",
            "-v",
            f"{run_dir}:/run",
            "--entrypoint",
            "python",
            "nexus-kokoro-tts",
            "/work/generate_file.py",
            "--text-file",
            "/run/input.txt",
            "--output",
            "/run/kokoro.wav",
            "--voice",
            request.voice,
            "--lang-code",
            request.lang_code,
        ],
        KOKORO_ROOT,
    )

    if not output_file.exists():
        raise error_response(500, "OUTPUT_MISSING", "Kokoro did not produce an output file.")

    return FileResponse(output_file, media_type="audio/wav", filename="kokoro.wav")


@app.post("/tts/vibevoice", response_class=FileResponse)
async def vibevoice_tts(request: VibeVoiceRequest) -> FileResponse:
    run_dir = make_run_dir("vibevoice")
    text_file = run_dir / "input.txt"
    output_dir = run_dir / "outputs"
    output_file = output_dir / "input_generated.wav"
    text_file.write_text(request.text, encoding="utf-8")

    await run_checked(
        ["./generate.sh", str(text_file), str(output_dir), request.speaker],
        VIBEVOICE_ROOT,
    )

    if not output_file.exists():
        raise error_response(500, "OUTPUT_MISSING", "VibeVoice did not produce an output file.")

    return FileResponse(output_file, media_type="audio/wav", filename="vibevoice.wav")


@app.post("/transcribe")
async def transcribe(audio: UploadFile = File(...)) -> dict[str, object]:
    run_dir = make_run_dir("whisper")
    input_name = Path(audio.filename or "audio.wav").name
    input_file = run_dir / input_name

    with input_file.open("wb") as target:
        shutil.copyfileobj(audio.file, target)

    await ensure_docker_image("whisper-docker-smoke", WHISPER_ROOT)
    await run_checked(
        [
            "docker",
            "run",
            "--rm",
            "-v",
            f"{run_dir}:/work",
            "-v",
            f"{WHISPER_ROOT / '.cache'}:/root/.cache/whisper",
            "whisper-docker-smoke",
            input_name,
            "--model",
            "tiny",
            "--language",
            "en",
            "--output_format",
            "txt",
            "--output_dir",
            "/work",
        ],
        WHISPER_ROOT,
    )

    transcript_file = run_dir / f"{input_file.stem}.txt"
    if not transcript_file.exists():
        raise error_response(500, "OUTPUT_MISSING", "Whisper did not produce a transcript.")

    return {"data": {"text": transcript_file.read_text(encoding="utf-8").strip()}}
