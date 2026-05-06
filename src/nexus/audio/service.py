from __future__ import annotations

import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, BinaryIO

from nexus.audio.models import AudioGenRequest
from nexus.audio.paths import AudioPaths, default_audio_paths
from nexus.models.policy import GEMMA_TEXT_MODEL_ID, QWEN_TTS_MODEL_ID

# Lazy imports keep the runtime light until a model-backed path is hit.
_qwen_tts_model = None
_gemma_audio_model = None


def _require_soundfile():
    try:
        import soundfile as sf
    except ImportError as exc:
        raise AudioError(
            503,
            "MISSING_DEPENDENCY",
            "soundfile is not installed. Install the runtime bundle to enable TTS and ASR.",
        ) from exc
    return sf


def _require_torch():
    try:
        import torch
    except ImportError as exc:
        raise AudioError(
            503,
            "MISSING_DEPENDENCY",
            "torch is not installed. Install the runtime bundle to enable TTS and ASR.",
        ) from exc
    return torch


@dataclass
class GemmaAudioModel:
    model_id: str
    processor: Any
    model: Any


def _get_qwen_tts_model():
    global _qwen_tts_model
    if _qwen_tts_model is None:
        from qwen_tts import Qwen3TTSModel

        torch = _require_torch()
        device = "cuda" if torch.cuda.is_available() else "cpu"
        _qwen_tts_model = Qwen3TTSModel.from_pretrained(
            QWEN_TTS_MODEL_ID,
            device_map=device,
            dtype=torch.bfloat16 if device == "cuda" else torch.float32,
        )
    return _qwen_tts_model


def _get_gemma_audio_model() -> GemmaAudioModel:
    global _gemma_audio_model
    if _gemma_audio_model is None:
        from transformers import AutoModelForMultimodalLM, AutoProcessor

        torch = _require_torch()
        device = "cuda" if torch.cuda.is_available() else "cpu"
        processor = AutoProcessor.from_pretrained(GEMMA_TEXT_MODEL_ID)
        model = AutoModelForMultimodalLM.from_pretrained(
            GEMMA_TEXT_MODEL_ID,
            device_map="auto",
            dtype=torch.bfloat16 if device == "cuda" else torch.float32,
        )
        model.eval()
        _gemma_audio_model = GemmaAudioModel(
            model_id=GEMMA_TEXT_MODEL_ID,
            processor=processor,
            model=model,
        )
    return _gemma_audio_model


def _parse_gemma_response(processor: Any, response: str) -> str:
    parser = getattr(processor, "parse_response", None)
    if callable(parser):
        try:
            parsed = parser(response)
        except Exception:
            parsed = None
        else:
            if isinstance(parsed, str):
                return parsed.strip()
            if isinstance(parsed, dict):
                for key in ("text", "content", "response"):
                    value = parsed.get(key)
                    if isinstance(value, str):
                        return value.strip()
            if parsed is not None:
                return str(parsed).strip()
    return response.strip()


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
    """Audio generation service using Qwen TTS.

    TTS remains on the purpose-built Qwen speech synthesis model. The service
    is intentionally separate from the Gemma audio-understanding path.
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
            "model": QWEN_TTS_MODEL_ID,
            "supported_speakers": self.SUPPORTED_SPEAKERS,
        }

    async def generate(self, request: AudioGenRequest) -> Path:
        """Generate speech from text using Qwen TTS."""
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
    """Automatic Speech Recognition and speech understanding via Gemma 4.

    Gemma 4 E2B-it handles audio understanding in this repository. The service
    transcribes uploaded audio into text and keeps the model path fixed.
    """

    def __init__(self, paths: AudioPaths | None = None) -> None:
        self.paths = paths or default_audio_paths()

    def health(self) -> dict[str, object]:
        return {
            "ok": True,
            "model": GEMMA_TEXT_MODEL_ID,
            "languages": 140,
        }

    async def transcribe(self, filename: str | None, fileobj: BinaryIO) -> str:
        """Transcribe audio to text using Gemma 4 E2B-it."""
        import io

        sf = _require_soundfile()
        gemma = _get_gemma_audio_model()

        audio_bytes = fileobj.read()

        with io.BytesIO(audio_bytes) as buffer:
            audio_data, sr = sf.read(buffer, dtype="float32")

        if getattr(audio_data, "ndim", 1) > 1:
            audio_data = audio_data.mean(axis=1).astype("float32")

        temp_dir = self.paths.runtime_root
        temp_dir.mkdir(parents=True, exist_ok=True)
        temp_audio = temp_dir / f"gemma_audio_{uuid.uuid4().hex}.wav"
        sf.write(str(temp_audio), audio_data, sr)

        try:
            messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "audio", "audio": str(temp_audio)},
                        {
                            "type": "text",
                            "text": (
                                "Transcribe the following speech segment in its original language. "
                                "Only output the transcription, with no extra formatting."
                            ),
                        },
                    ],
                }
            ]

            inputs = gemma.processor.apply_chat_template(
                messages,
                tokenize=True,
                return_dict=True,
                return_tensors="pt",
                add_generation_prompt=True,
            ).to(gemma.model.device)
            input_len = inputs["input_ids"].shape[-1]

            torch = _require_torch()
            with torch.inference_mode():
                outputs = gemma.model.generate(
                    **inputs,
                    max_new_tokens=256,
                    do_sample=False,
                    pad_token_id=getattr(gemma.processor.tokenizer, "eos_token_id", None) or 0,
                )

            response = gemma.processor.decode(outputs[0][input_len:], skip_special_tokens=True)
            text = _parse_gemma_response(gemma.processor, response)
        finally:
            temp_audio.unlink(missing_ok=True)

        return text


class AudioService:
    """Audio service using Qwen TTS and Gemma 4 ASR.

    The repository policy is:
      - Gemma 4 E2B-it for audio understanding / transcription
      - Qwen TTS for speech synthesis
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
        """Synthesize speech from text using Qwen TTS."""
        return await self._tts_service.generate(request)

    async def transcribe(self, filename: str | None, fileobj: BinaryIO) -> str:
        """Transcribe audio to text using Gemma 4 E2B-it."""
        return await self._asr_service.transcribe(filename, fileobj)
