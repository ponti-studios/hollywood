from __future__ import annotations

import uuid
from pathlib import Path
from typing import BinaryIO

from nexus.audio.models import AudioGenRequest
from nexus.audio.paths import AudioPaths, default_audio_paths

# Lazy imports for Qwen models
_qwen_tts_model = None
_qwen_asr_model = None


def _get_qwen_tts_model():
    global _qwen_tts_model
    if _qwen_tts_model is None:
        from qwen_tts import Qwen3TTSModel

        torch = _require_torch()
        device = "cuda" if torch.cuda.is_available() else "cpu"
        _qwen_tts_model = Qwen3TTSModel.from_pretrained(
            "Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice",
            device_map=device,
            dtype=torch.bfloat16 if device == "cuda" else torch.float32,
        )
    return _qwen_tts_model


def _get_qwen_asr_model():
    global _qwen_asr_model
    if _qwen_asr_model is None:
        from qwen_asr import QwenASRModel

        torch = _require_torch()
        device = "cuda" if torch.cuda.is_available() else "cpu"
        _qwen_asr_model = QwenASRModel(
            model="Qwen/Qwen3-ASR-1.7B",
            device=device,
            dtype=torch.bfloat16 if device == "cuda" else torch.float32,
        )
    return _qwen_asr_model


def _require_soundfile():
    try:
        import soundfile as sf
    except ImportError as exc:
        raise AudioError(
            503,
            "MISSING_DEPENDENCY",
            "soundfile is not installed. Install the audio extras to enable TTS and ASR.",
        ) from exc
    return sf


def _require_torch():
    try:
        import torch
    except ImportError as exc:
        raise AudioError(
            503,
            "MISSING_DEPENDENCY",
            "torch is not installed. Install the audio extras to enable TTS and ASR.",
        ) from exc
    return torch


class AudioError(Exception):
    def __init__(
        self, status_code: int, code: str, message: str, details: str | None = None
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details


class AudioGenService:
    """Audio generation service using Qwen3 TTS.

    Provides text-to-speech via the qwen-tts package with support for
    multiple speakers and natural language instructions.
    """

    SUPPORTED_SPEAKERS = [
        "aiden",
        "dylan",
        "eric",
        "ono_anna",
        "ryan",
        "serena",
        "sohee",
        "uncle_fu",
        "vivian",
    ]

    def __init__(self, paths: AudioPaths | None = None) -> None:
        self.paths = paths or default_audio_paths()

    def health(self) -> dict[str, object]:
        return {
            "ok": True,
            "model": "Qwen3-TTS-12Hz-1.7B-CustomVoice",
            "supported_speakers": self.SUPPORTED_SPEAKERS,
        }

    async def generate(self, request: AudioGenRequest) -> Path:
        """Generate speech from text using Qwen3 TTS."""
        sf = _require_soundfile()
        model = _get_qwen_tts_model()

        speaker = request.speaker
        if speaker not in self.SUPPORTED_SPEAKERS:
            raise AudioError(
                400,
                "INVALID_SPEAKER",
                f"Speaker '{speaker}' not supported. Use one of: {self.SUPPORTED_SPEAKERS}",
            )

        wavs, sr = model.generate_custom_voice(
            text=request.text,
            language=request.language,
            speaker=speaker,
            instruct=request.instruct,
        )

        run_dir = self._make_run_dir("tts")
        output_file = run_dir / "audio.wav"
        sf.write(str(output_file), wavs[0], sr)
        return output_file

    def _make_run_dir(self, prefix: str) -> Path:
        self.paths.runtime_root.mkdir(parents=True, exist_ok=True)
        run_dir = self.paths.runtime_root / f"{prefix}-{uuid.uuid4().hex}"
        run_dir.mkdir(parents=True, exist_ok=False)
        return run_dir


class ASRService:
    """Automatic Speech Recognition service using Qwen3 ASR.

    Provides transcription via the qwen-asr package with support for
    52 languages and dialects.
    """

    def __init__(self, paths: AudioPaths | None = None) -> None:
        self.paths = paths or default_audio_paths()

    def health(self) -> dict[str, object]:
        return {
            "ok": True,
            "model": "Qwen3-ASR-1.7B",
            "languages": 52,
        }

    async def transcribe(self, filename: str | None, fileobj: BinaryIO) -> str:
        """Transcribe audio to text using Qwen3 ASR."""
        import io

        sf = _require_soundfile()
        model = _get_qwen_asr_model()

        # Read audio bytes
        audio_bytes = fileobj.read()

        # Save to temp file for qwen-asr
        with io.BytesIO(audio_bytes) as buffer:
            audio_data, sr = sf.read(buffer)

        # Create temp file
        run_dir = self.paths.runtime_root
        run_dir.mkdir(parents=True, exist_ok=True)
        temp_audio = run_dir / f"temp_{uuid.uuid4().hex}.wav"
        sf.write(str(temp_audio), audio_data, sr)

        try:
            # Transcribe
            result = model.transcribe(str(temp_audio))
            text = result["text"]
        finally:
            # Cleanup temp file
            temp_audio.unlink(missing_ok=True)

        return text

    def _make_run_dir(self, prefix: str) -> Path:
        self.paths.runtime_root.mkdir(parents=True, exist_ok=True)
        run_dir = self.paths.runtime_root / f"{prefix}-{uuid.uuid4().hex}"
        run_dir.mkdir(parents=True, exist_ok=False)
        return run_dir


class AudioService:
    """Audio service using Qwen models for both TTS and ASR.

    Delegates work to local Qwen models (TTS and ASR).
    """

    def __init__(self, paths: AudioPaths | None = None) -> None:
        self.paths = paths or default_audio_paths()
        self._tts_service = AudioGenService(paths)
        self._asr_service = ASRService(paths)

    def health(self) -> dict[str, object]:
        return {
            "ok": True,
            "tts": self._tts_service.health(),
            "asr": self._asr_service.health(),
        }

    async def tts(self, request: AudioGenRequest) -> Path:
        """Synthesize speech from text using Qwen3 TTS."""
        return await self._tts_service.generate(request)

    async def transcribe(self, filename: str | None, fileobj: BinaryIO) -> str:
        """Transcribe audio to text using Qwen3 ASR."""
        return await self._asr_service.transcribe(filename, fileobj)
