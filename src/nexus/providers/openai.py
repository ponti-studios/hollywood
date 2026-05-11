from __future__ import annotations

import base64
import os
from dataclasses import dataclass
from typing import Any

import httpx

DEFAULT_OPENAI_BASE_URL = "https://api.openai.com/v1"
DEFAULT_OPENAI_TEXT_MODEL = "gpt-4.1-mini"
DEFAULT_OPENAI_IMAGE_MODEL = "gpt-4.1-mini"
DEFAULT_OPENAI_TTS_MODEL = "gpt-4o-mini-tts"
DEFAULT_OPENAI_STT_MODEL = "gpt-4o-mini-transcribe"
DEFAULT_OPENAI_TTS_VOICE = "alloy"


class OpenAIError(RuntimeError):
    """Raised when the OpenAI API cannot fulfill a request."""


@dataclass(slots=True)
class OpenAITextResult:
    text: str
    model: str
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    raw: dict[str, Any] | None = None


@dataclass(slots=True)
class OpenAIAudioResult:
    audio_bytes: bytes
    mime_type: str
    model: str
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    raw: dict[str, Any] | None = None


class OpenAIClient:
    def __init__(
        self,
        *,
        base_url: str | None = None,
        text_model: str | None = None,
        audio_model: str | None = None,
        image_model: str | None = None,
        speech_voice: str | None = None,
        timeout: float = 120.0,
    ) -> None:
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.text_model = text_model or os.getenv("OPENAI_TEXT_MODEL") or DEFAULT_OPENAI_TEXT_MODEL
        self.image_model = (
            image_model or os.getenv("OPENAI_IMAGE_MODEL") or DEFAULT_OPENAI_IMAGE_MODEL
        )
        self.tts_model = (
            os.getenv("OPENAI_TTS_MODEL")
            or audio_model
            or os.getenv("OPENAI_AUDIO_MODEL")
            or DEFAULT_OPENAI_TTS_MODEL
        )
        self.stt_model = (
            os.getenv("OPENAI_STT_MODEL")
            or audio_model
            or os.getenv("OPENAI_AUDIO_MODEL")
            or DEFAULT_OPENAI_STT_MODEL
        )
        self.speech_voice = (
            speech_voice or os.getenv("OPENAI_SPEECH_VOICE") or DEFAULT_OPENAI_TTS_VOICE
        )
        self.base_url = (base_url or os.getenv("OPENAI_BASE_URL") or DEFAULT_OPENAI_BASE_URL).rstrip(
            "/"
        )
        headers: dict[str, str] = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        self._client = httpx.AsyncClient(base_url=self.base_url, timeout=timeout, headers=headers)

    @property
    def audio_model(self) -> str:
        return self.tts_model

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key)

    @property
    def auth_mode(self) -> str:
        return "api_key"

    async def aclose(self) -> None:
        await self._client.aclose()

    async def health(self) -> bool:
        if not self.is_configured:
            return False
        try:
            response = await self._request("GET", "/models")
            return response.status_code == 200
        except Exception:
            return False

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
        files: dict[str, tuple[str, bytes, str]] | None = None,
    ) -> httpx.Response:
        if not self.api_key:
            raise OpenAIError("OPENAI_API_KEY is required for OpenAI access.")
        try:
            response = await self._client.request(method, path, json=json, data=data, files=files)
            response.raise_for_status()
            return response
        except httpx.HTTPError as exc:
            raise OpenAIError(str(exc)) from exc

    async def _request_json(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
        files: dict[str, tuple[str, bytes, str]] | None = None,
    ) -> dict[str, Any]:
        response = await self._request(method, path, json=json, data=data, files=files)
        return response.json()

    async def reply(
        self,
        *,
        prompt: str,
        model: str | None = None,
        max_tokens: int = 512,
        temperature: float = 0.7,
        top_p: float = 0.9,
        stop: list[str] | None = None,
        system: str | None = None,
    ) -> OpenAITextResult:
        return await self.chat(
            messages=[{"role": "user", "content": prompt}],
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            top_p=top_p,
            stop=stop,
            system=system,
        )

    async def chat(
        self,
        *,
        messages: list[dict[str, str]],
        model: str | None = None,
        max_tokens: int = 512,
        temperature: float = 0.7,
        top_p: float = 0.9,
        stop: list[str] | None = None,
        system: str | None = None,
    ) -> OpenAITextResult:
        payload_messages = _build_chat_messages(messages, system)
        payload: dict[str, Any] = {
            "model": model or self.text_model,
            "messages": payload_messages,
            "temperature": temperature,
            "top_p": top_p,
            "max_tokens": max_tokens,
        }
        if stop:
            payload["stop"] = stop
        data = await self._request_json("POST", "/chat/completions", json=payload)
        text = _extract_chat_text(data)
        usage = data.get("usage") or {}
        return OpenAITextResult(
            text=text,
            model=str(data.get("model") or payload["model"]),
            prompt_tokens=_as_int(usage.get("prompt_tokens")),
            completion_tokens=_as_int(usage.get("completion_tokens")),
            raw=data,
        )

    async def analyze_image(
        self,
        *,
        image_bytes: bytes,
        mime_type: str,
        prompt: str,
        model: str | None = None,
        max_tokens: int = 512,
        temperature: float = 0.2,
        top_p: float = 0.9,
    ) -> OpenAITextResult:
        payload = {
            "model": model or self.image_model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime_type};base64,{base64.b64encode(image_bytes).decode('utf-8')}"
                            },
                        },
                    ],
                }
            ],
            "temperature": temperature,
            "top_p": top_p,
            "max_tokens": max_tokens,
        }
        data = await self._request_json("POST", "/chat/completions", json=payload)
        text = _extract_chat_text(data)
        usage = data.get("usage") or {}
        return OpenAITextResult(
            text=text,
            model=str(data.get("model") or payload["model"]),
            prompt_tokens=_as_int(usage.get("prompt_tokens")),
            completion_tokens=_as_int(usage.get("completion_tokens")),
            raw=data,
        )

    async def transcribe_audio(
        self,
        *,
        audio_bytes: bytes,
        mime_type: str,
        language: str = "auto",
        enhance: bool = False,
        model: str | None = None,
    ) -> OpenAITextResult:
        data: dict[str, Any] = {
            "model": model or self.stt_model,
            "response_format": "json",
        }
        if language and language != "auto":
            data["language"] = language
        if enhance:
            data["prompt"] = (
                "Transcribe this audio verbatim. Clean up obvious transcription errors without changing meaning."
            )

        filename = f"transcript{_suffix_for_mime(mime_type)}"
        files = {"file": (filename, audio_bytes, mime_type)}
        response = await self._request("POST", "/audio/transcriptions", data=data, files=files)
        payload = (
            response.json()
            if response.headers.get("content-type", "").startswith("application/json")
            else {"text": response.text}
        )
        text = str(payload.get("text") or "").strip()
        usage = payload.get("usage") or {}
        return OpenAITextResult(
            text=text,
            model=str(payload.get("model") or data["model"]),
            prompt_tokens=_as_int(usage.get("prompt_tokens")),
            completion_tokens=_as_int(usage.get("completion_tokens")),
            raw=payload,
        )

    async def synthesize_speech(
        self,
        *,
        text: str,
        model: str | None = None,
        voice: str | None = None,
        mime_type: str = "audio/wav",
        max_tokens: int = 64,
    ) -> OpenAIAudioResult:
        response_format = _response_format_for_mime(mime_type)
        payload = {
            "model": model or self.tts_model,
            "input": text,
            "voice": voice or self.speech_voice,
            "response_format": response_format,
        }
        response = await self._request("POST", "/audio/speech", json=payload)
        audio_bytes = response.content
        if not audio_bytes:
            raise OpenAIError("OpenAI did not return audio bytes for text-to-speech.")
        return OpenAIAudioResult(
            audio_bytes=audio_bytes,
            mime_type=mime_type,
            model=str(payload["model"]),
            prompt_tokens=None,
            completion_tokens=None,
            raw={"response_format": response_format},
        )


_client: OpenAIClient | None = None


def get_openai_client() -> OpenAIClient:
    global _client
    if _client is None:
        _client = OpenAIClient()
    return _client


def _build_chat_messages(messages: list[dict[str, str]], system: str | None) -> list[dict[str, str]]:
    payload_messages: list[dict[str, str]] = []
    if system:
        payload_messages.append({"role": "system", "content": system})
    for message in messages:
        role = message.get("role")
        content = message.get("content", "")
        if role == "system":
            payload_messages.append({"role": "system", "content": content})
            continue
        mapped_role = "assistant" if role == "assistant" else "user"
        payload_messages.append({"role": mapped_role, "content": content})
    return payload_messages


def _extract_chat_text(payload: dict[str, Any]) -> str:
    choices = payload.get("choices") or []
    if not choices:
        return ""
    choice = choices[0] if isinstance(choices[0], dict) else {}
    message = choice.get("message") or {}
    content = message.get("content")
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        texts: list[str] = []
        for item in content:
            if not isinstance(item, dict):
                continue
            text = item.get("text")
            if isinstance(text, str):
                texts.append(text)
        return "".join(texts).strip()
    return ""


def _response_format_for_mime(mime_type: str) -> str:
    return {
        "audio/wav": "wav",
        "audio/mpeg": "mp3",
        "audio/opus": "opus",
        "audio/aac": "aac",
        "audio/flac": "flac",
        "audio/L16": "pcm",
    }.get(mime_type, "wav")


def _suffix_for_mime(mime_type: str) -> str:
    return {
        "audio/wav": ".wav",
        "audio/mpeg": ".mp3",
        "audio/opus": ".opus",
        "audio/aac": ".aac",
        "audio/flac": ".flac",
        "audio/L16": ".pcm",
    }.get(mime_type, ".wav")


def _as_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
