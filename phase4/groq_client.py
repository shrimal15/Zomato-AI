"""Groq chat completions. A missing key, timeout, or HTTP error never hangs the request."""

import json
import os
import socket
import urllib.error
import urllib.request
from pathlib import Path

from app.config import ROOT

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
# llama-3.3-70b-versatile was shut down for developer plans on 2026-08-16.
DEFAULT_MODEL = "openai/gpt-oss-120b"
DEFAULT_TIMEOUT_SECONDS = 20.0


class GroqError(Exception):
    """The completion cannot be used. Phase 4 falls back to catalog facts."""


class GroqClient:
    """OpenAI-compatible Groq client. Pass api_key to skip the environment and .env."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        if api_key is None:
            load_local_env()
            api_key = os.environ.get("GROQ_API_KEY", "")
        self.api_key = api_key.strip()
        if model is None:
            model = os.environ.get("GROQ_MODEL", DEFAULT_MODEL)
        self.model = model.strip() or DEFAULT_MODEL
        self.timeout = timeout

    def complete(self, messages: list[dict[str, str]]) -> str:
        if not self.api_key:
            raise GroqError("missing api key")
        body = json.dumps(
            {
                "model": self.model,
                "messages": messages,
                "temperature": 0.2,
                "max_tokens": 1024,
                "response_format": {"type": "json_object"},
            }
        ).encode("utf-8")
        request = urllib.request.Request(
            GROQ_URL,
            data=body,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "User-Agent": "zomato-recommendations/0.1",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            if error.code == 429:
                raise GroqError("rate limit") from error
            raise GroqError(f"http {error.code}") from error
        except (TimeoutError, socket.timeout) as error:
            raise GroqError("timeout") from error
        except urllib.error.URLError as error:
            if isinstance(error.reason, (TimeoutError, socket.timeout)):
                raise GroqError("timeout") from error
            raise GroqError("request failed") from error
        return _message_text(payload)


def load_local_env(path: Path | None = None) -> None:
    """Load KEY=VALUE lines from .env without overriding variables already set."""
    env_path = path or (ROOT / ".env")
    if not env_path.is_file():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        key = key.strip()
        if key.startswith("export "):
            key = key.removeprefix("export ").strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]
        if key and key not in os.environ:
            os.environ[key] = value


def _message_text(payload: object) -> str:
    if not isinstance(payload, dict):
        raise GroqError("unexpected response")
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        raise GroqError("unexpected response")
    message = choices[0].get("message") if isinstance(choices[0], dict) else None
    if not isinstance(message, dict):
        raise GroqError("unexpected response")
    content = message.get("content")
    if isinstance(content, list):
        parts: list[str] = []
        for part in content:
            if isinstance(part, str):
                parts.append(part)
            elif isinstance(part, dict) and isinstance(part.get("text"), str):
                parts.append(part["text"])
        content = "".join(parts)
    if not isinstance(content, str) or not content.strip():
        raise GroqError("empty completion")
    return content
