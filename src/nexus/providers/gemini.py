from __future__ import annotations

import base64
import os
from dataclasses import dataclass
from typing import Any

import httpx

DEFAULT_GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
DEFAULT_GEMINI_TEXT_MODEL = "gemini-2.5-flash"
DEFAULT_GEMINI_AUDIO_MODEL = "gemini-2.5-flash"
DEFAULT_GEMINI_IMAGE_MODEL = "gemini-2.5-flash"
DEFAULT_GEMINI_SPEECH_VOICE = "Kore"


class GeminiError(RuntimeError):
    """Raised when the Gemini API cannot fulfill a request."""


@dataclass(slots=True)
class GeminiTextResult:
    text: str
    model: str
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    raw: dict[str, Any] | None = None


@dataclass(slots=True)
class GeminiAudioResult:
    audio_bytes: bytes
    mime_type: str
    model: str
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    raw: dict[str, Any] | None = None


class GeminiClient:
    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        text_model: str | None = None,
        audio_model: str | None = None,
        image_model: str | None = None,
        speech_voice: str | None = None,
        timeout: float = 120.0,
    ) -> None:
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.base_url = (
            base_url or os.getenv("GEMINI_BASE_URL") or DEFAULT_GEMINI_BASE_URL
        ).rstrip("/")
        self.text_model = text_model or os.getenv("GEMINI_TEXT_MODEL") or DEFAULT_GEMINI_TEXT_MODEL
        self.audio_model = (
            audio_model or os.getenv("GEMINI_AUDIO_MODEL") or DEFAULT_GEMINI_AUDIO_MODEL
        )
        self.image_model = (
            image_model or os.getenv("GEMINI_IMAGE_MODEL") or DEFAULT_GEMINI_IMAGE_MODEL
        )
        self.speech_voice = (
            speech_voice or os.getenv("GEMINI_SPEECH_VOICE") or DEFAULT_GEMINI_SPEECH_VOICE
        )
        params = {"key": self.api_key} if self.api_key else None
        self._client = httpx.AsyncClient(base_url=self.base_url, timeout=timeout, params=params)

    async def aclose(self) -> None:
        await self._client.aclose()

    async def health(self) -> bool:
        if not self.api_key:
            return False
        try:
            response = await self._client.get("/models")
            return response.status_code == 200
        except Exception:
            return False

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
    ) -> GeminiTextResult:
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
    ) -> GeminiTextResult:
        payload = self._build_text_payload(
            messages=messages,
            model=model or self.text_model,
            max_tokens=max_tokens,
            temperature=temperature,
            top_p=top_p,
            stop=stop,
            system=system,
        )
        data = await self._post_json(f"/models/{payload['model']}:generateContent", payload["body"])
        text = _extract_text(data)
        usage = data.get("usageMetadata") or {}
        return GeminiTextResult(
            text=text,
            model=str(data.get("modelVersion") or payload["model"]),
            prompt_tokens=_as_int(usage.get("promptTokenCount")),
            completion_tokens=_as_int(usage.get("candidatesTokenCount")),
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
    ) -> GeminiTextResult:
        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [
                        {"text": prompt},
                        {
                            "inlineData": {
                                "mimeType": mime_type,
                                "data": base64.b64encode(image_bytes).decode("utf-8"),
                            }
                        },
                    ],
                }
            ],
            "generationConfig": {
                "temperature": temperature,
                "topP": top_p,
                "maxOutputTokens": max_tokens,
            },
        }
        data = await self._post_json(
            f"/models/{model or self.image_model}:generateContent",
            payload,
        )
        text = _extract_text(data)
        usage = data.get("usageMetadata") or {}
        return GeminiTextResult(
            text=text,
            model=str(data.get("modelVersion") or model or self.image_model),
            prompt_tokens=_as_int(usage.get("promptTokenCount")),
            completion_tokens=_as_int(usage.get("candidatesTokenCount")),
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
    ) -> GeminiTextResult:
        prompt = (
            "Transcribe this audio verbatim. Preserve the original language, punctuation, and names. "
            "Return only the transcript."
        )
        if language and language != "auto":
            prompt += f" The expected language is {language}."
        if enhance:
            prompt += " Clean up obvious transcription errors without changing meaning."

        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [
                        {"text": prompt},
                        {
                            "inlineData": {
                                "mimeType": mime_type,
                                "data": base64.b64encode(audio_bytes).decode("utf-8"),
                            }
                        },
                    ],
                }
            ],
            "generationConfig": {
                "temperature": 0.0,
                "topP": 0.1,
                "maxOutputTokens": 1024,
            },
        }
        data = await self._post_json(
            f"/models/{model or self.audio_model}:generateContent",
            payload,
        )
        text = _extract_text(data)
        usage = data.get("usageMetadata") or {}
        return GeminiTextResult(
            text=text,
            model=str(data.get("modelVersion") or model or self.audio_model),
            prompt_tokens=_as_int(usage.get("promptTokenCount")),
            completion_tokens=_as_int(usage.get("candidatesTokenCount")),
            raw=data,
        )

    async def synthesize_speech(
        self,
        *,
        text: str,
        model: str | None = None,
        voice: str | None = None,
        mime_type: str = "audio/wav",
        max_tokens: int = 64,
    ) -> GeminiAudioResult:
        payload = {
            "contents": [
                {"role": "user", "parts": [{"text": text}]},
            ],
            "generationConfig": {
                "responseModalities": ["AUDIO"],
                "maxOutputTokens": max_tokens,
                "speechConfig": {
                    "voiceConfig": {
                        "prebuiltVoiceConfig": {"voiceName": voice or self.speech_voice}
                    }
                },
            },
        }
        data = await self._post_json(
            f"/models/{model or self.audio_model}:generateContent",
            payload,
        )
        audio_bytes = _extract_audio_bytes(data)
        if audio_bytes is None:
            raise GeminiError(
                "Gemini did not return audio bytes. Check the configured audio model and speech settings."
            )
        usage = data.get("usageMetadata") or {}
        return GeminiAudioResult(
            audio_bytes=audio_bytes,
            mime_type=mime_type,
            model=str(data.get("modelVersion") or model or self.audio_model),
            prompt_tokens=_as_int(usage.get("promptTokenCount")),
            completion_tokens=_as_int(usage.get("candidatesTokenCount")),
            raw=data,
        )

    async def _post_json(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            response = await self._client.post(path, json=payload)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as exc:
            raise GeminiError(str(exc)) from exc

    def _build_text_payload(
        self,
        *,
        messages: list[dict[str, str]],
        model: str,
        max_tokens: int,
        temperature: float,
        top_p: float,
        stop: list[str] | None,
        system: str | None,
    ) -> dict[str, Any]:
        system_texts: list[str] = []
        contents: list[dict[str, Any]] = []
        for message in messages:
            role = message.get("role")
            content = message.get("content", "")
            if role == "system":
                system_texts.append(content)
                continue
            mapped_role = "model" if role == "assistant" else "user"
            contents.append({"role": mapped_role, "parts": [{"text": content}]})

        if system:
            system_texts.append(system)

        body: dict[str, Any] = {
            "model": model,
            "body": {
                "contents": contents,
                "generationConfig": {
                    "temperature": temperature,
                    "topP": top_p,
                    "maxOutputTokens": max_tokens,
                },
            },
        }
        if stop:
            body["body"]["generationConfig"]["stopSequences"] = stop
        if system_texts:
            body["body"]["systemInstruction"] = {"parts": [{"text": "\n\n".join(system_texts)}]}
        return body


_client: GeminiClient | None = None


def get_gemini_client() -> GeminiClient:
    global _client
    if _client is None:
        _client = GeminiClient()
    return _client


def _extract_text(payload: dict[str, Any]) -> str:
    candidates = payload.get("candidates") or []
    if not candidates:
        return ""
    candidate = candidates[0] if isinstance(candidates[0], dict) else {}
    content = candidate.get("content") or {}
    parts = content.get("parts") or []
    texts: list[str] = []
    for part in parts:
        if not isinstance(part, dict):
            continue
        text = part.get("text")
        if isinstance(text, str):
            texts.append(text)
    return "".join(texts).strip()


def _extract_audio_bytes(payload: dict[str, Any]) -> bytes | None:
    candidates = payload.get("candidates") or []
    if not candidates:
        return None
    candidate = candidates[0] if isinstance(candidates[0], dict) else {}
    content = candidate.get("content") or {}
    parts = content.get("parts") or []
    for part in parts:
        if not isinstance(part, dict):
            continue
        inline = part.get("inlineData") or part.get("inline_data")
        if isinstance(inline, dict):
            data = inline.get("data")
            if isinstance(data, str) and data:
                return base64.b64decode(data)
    return None


def _as_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
