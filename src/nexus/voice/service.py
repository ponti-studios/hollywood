from __future__ import annotations

import asyncio
import shutil
import subprocess
import uuid
from pathlib import Path
from typing import BinaryIO

from nexus.voice.models import KokoroRequest
from nexus.voice.paths import VoicePaths, default_voice_paths


class VoiceError(Exception):
    def __init__(self, status_code: int, code: str, message: str, details: str | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details


class VoiceService:
    def __init__(self, paths: VoicePaths | None = None) -> None:
        self.paths = paths or default_voice_paths()

    def health(self) -> dict[str, object]:
        return {
            "ok": True,
            "kokoro_image": "nexus-kokoro-tts",
            "whisper_image": "whisper-docker-smoke",
        }

    async def kokoro_tts(self, request: KokoroRequest) -> Path:
        run_dir = self._make_run_dir("kokoro")
        text_file = run_dir / "input.txt"
        output_file = run_dir / "kokoro.wav"
        text_file.write_text(request.text, encoding="utf-8")

        await self._ensure_docker_image("nexus-kokoro-tts", self.paths.images_root / "tts.dockerfile")
        await self._run_checked(
            [
                "docker",
                "run",
                "--rm",
                "-v",
                f"{self.paths.kokoro_root}:/work",
                "-v",
                f"{self.paths.kokoro_root / '.cache'}:/root/.cache",
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
            self.paths.kokoro_root,
        )

        if not output_file.exists():
            raise VoiceError(500, "OUTPUT_MISSING", "Kokoro did not produce an output file.")

        return output_file

    async def transcribe(self, filename: str | None, fileobj: BinaryIO) -> str:
        run_dir = self._make_run_dir("whisper")
        input_name = Path(filename or "audio.wav").name
        input_file = run_dir / input_name

        with input_file.open("wb") as target:
            shutil.copyfileobj(fileobj, target)

        await self._ensure_docker_image("whisper-docker-smoke", self.paths.images_root / "stt.dockerfile")
        await self._run_checked(
            [
                "docker",
                "run",
                "--rm",
                "-v",
                f"{run_dir}:/work",
                "-v",
                f"{self.paths.whisper_root / '.cache'}:/root/.cache/whisper",
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
            self.paths.whisper_root,
        )

        transcript_file = run_dir / f"{input_file.stem}.txt"
        if not transcript_file.exists():
            raise VoiceError(500, "OUTPUT_MISSING", "Whisper did not produce a transcript.")

        return transcript_file.read_text(encoding="utf-8").strip()

    def _make_run_dir(self, prefix: str) -> Path:
        self.paths.runtime_root.mkdir(parents=True, exist_ok=True)
        run_dir = self.paths.runtime_root / f"{prefix}-{uuid.uuid4().hex}"
        run_dir.mkdir(parents=True, exist_ok=False)
        return run_dir

    async def _ensure_docker_image(self, image: str, dockerfile: Path) -> None:
        result = await asyncio.to_thread(
            self._run_command,
            ["docker", "image", "inspect", image],
            self.paths.repo_root,
        )
        if result.returncode == 0:
            return

        await self._run_checked(
            ["docker", "build", "-f", str(dockerfile), "-t", image, "."],
            self.paths.repo_root,
        )

    async def _run_checked(self, command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
        result = await asyncio.to_thread(self._run_command, command, cwd)
        if result.returncode != 0:
            raise VoiceError(
                500,
                "RUNNER_FAILED",
                "The model runner failed.",
                (result.stderr or result.stdout)[-4000:],
            )
        return result

    @staticmethod
    def _run_command(command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(command, cwd=cwd, text=True, capture_output=True, check=False)
