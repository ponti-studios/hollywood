from __future__ import annotations

import base64
from dataclasses import dataclass
from typing import Any

import httpx

from nexus.env import (
    DEFAULT_OPENROUTER_BASE_URL,
    DEFAULT_OPENROUTER_IMAGE_MODEL,
    DEFAULT_OPENROUTER_TEXT_MODEL,
    get_settings,
)


class OpenRouterError(RuntimeError):
    """Raised when the OpenRouter API cannot fulfill a request."""


@dataclass(slots=True)
class OpenRouterTextResult:
    text: str
    model: str
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    raw: dict[str, Any] | None = None


class OpenRouterClient:
    def __init__(self, *, timeout: float = 120.0) -> None:
        settings = get_settings()
        self.api_key = settings.openrouter_api_key
        self.text_model = settings.openrouter_text_model or DEFAULT_OPENROUTER_TEXT_MODEL
        self.image_model = settings.openrouter_image_model or DEFAULT_OPENROUTER_IMAGE_MODEL
        self.base_url = (settings.openrouter_base_url or DEFAULT_OPENROUTER_BASE_URL).rstrip("/")
        headers: dict[str, str] = {
            "HTTP-Referer": "https://github.com/ponti-studios/nexus",
            "X-Title": "Nexus",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        self._client = httpx.AsyncClient(base_url=self.base_url, timeout=timeout, headers=headers)

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key)

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
    ) -> httpx.Response:
        if not self.api_key:
            raise OpenRouterError("OPENROUTER_API_KEY is required for OpenRouter access.")
        try:
            response = await self._client.request(method, path, json=json)
            response.raise_for_status()
            return response
        except httpx.HTTPError as exc:
            raise OpenRouterError(str(exc)) from exc

    async def _request_json(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        response = await self._request(method, path, json=json)
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
    ) -> OpenRouterTextResult:
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
    ) -> OpenRouterTextResult:
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
        return OpenRouterTextResult(
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
    ) -> OpenRouterTextResult:
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
        return OpenRouterTextResult(
            text=text,
            model=str(data.get("model") or payload["model"]),
            prompt_tokens=_as_int(usage.get("prompt_tokens")),
            completion_tokens=_as_int(usage.get("completion_tokens")),
            raw=data,
        )


_client: OpenRouterClient | None = None


def get_openrouter_client() -> OpenRouterClient:
    global _client
    if _client is None:
        _client = OpenRouterClient()
    return _client


def _build_chat_messages(
    messages: list[dict[str, str]], system: str | None
) -> list[dict[str, str]]:
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


def _as_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
