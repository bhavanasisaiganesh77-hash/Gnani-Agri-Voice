"""Replaceable LLM layer for agricultural reasoning.

Providers implement the small LLMProvider interface. Pick one with LLM_PROVIDER:
  anthropic          -> Claude, through Anthropic's Messages API (default)
  openai_compatible  -> any OpenAI-compatible chat API (LLM_API_KEY, LLM_BASE_URL, LLM_MODEL)

Claude is NOT a Gnani model. Gnani supplies speech (Prisma STT, Timbre TTS) only.

Anthropic Messages API (docs.anthropic.com): POST https://api.anthropic.com/v1/messages
headers x-api-key, anthropic-version: 2023-06-01; body {model, max_tokens, system, messages}.
Images are sent as base64 content blocks. Keys come from the environment or Streamlit secrets and are never logged.
"""

import base64
import logging
import os
from abc import ABC, abstractmethod

import requests

import llm_client  # OpenAI-compatible transport and secret lookup (kept from the original app)

log = logging.getLogger("agrivoice.llm")
ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VERSION = "2023-06-01"
DEFAULT_ANTHROPIC_MODEL = "claude-sonnet-5-5"
TIMEOUT_SECONDS = 60
IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}


class LlmError(Exception):
    """Any provider problem. `kind` is one of: not_configured, auth, rate_limit, busy, timeout, bad_reply, request."""

    def __init__(self, kind: str, detail: str = ""):
        super().__init__(kind)
        self.kind = kind
        self.detail = detail


class LLMProvider(ABC):
    name = "base"
    supports_images = False

    @abstractmethod
    def is_configured(self) -> bool: ...

    @abstractmethod
    def generate(self, system: str, messages: list, max_tokens: int = 900, temperature: float = 0.3,
                 image: tuple | None = None) -> str:
        """messages: [{'role': 'user'|'assistant', 'content': str}], ending with a user turn.
        image: optional (bytes, media_type) attached to the LAST user message."""


class AnthropicProvider(LLMProvider):
    name = "anthropic"
    supports_images = True

    def _key(self): return llm_client._secret("ANTHROPIC_API_KEY")
    def _model(self): return llm_client._secret("ANTHROPIC_MODEL") or DEFAULT_ANTHROPIC_MODEL
    def is_configured(self) -> bool: return bool(self._key())

    def generate(self, system, messages, max_tokens=900, temperature=0.3, image=None):
        key = self._key()
        if not key:
            raise LlmError("not_configured")
        payload_msgs = [{"role": m["role"], "content": m["content"]} for m in messages]
        if image:
            data, media_type = image
            if media_type not in IMAGE_TYPES:
                raise LlmError("request", "unsupported image type")
            last = payload_msgs[-1]
            last["content"] = [
                {"type": "image", "source": {"type": "base64", "media_type": media_type,
                                             "data": base64.b64encode(data).decode("ascii")}},
                {"type": "text", "text": last["content"]},
            ]
        body = {"model": self._model(), "max_tokens": max_tokens, "temperature": temperature,
                "system": system, "messages": payload_msgs}
        response = None
        try:
            response = llm_client._session().post(
                ANTHROPIC_URL, json=body, timeout=TIMEOUT_SECONDS,
                headers={"x-api-key": key, "anthropic-version": ANTHROPIC_VERSION, "content-type": "application/json"})
            response.raise_for_status()
            blocks = response.json().get("content") or []
            text = "".join(b.get("text", "") for b in blocks if b.get("type") == "text").strip()
        except requests.Timeout:
            raise LlmError("timeout")
        except requests.HTTPError:
            status = response.status_code if response is not None else 0
            log.warning("anthropic returned HTTP %s", status)  # status only: never the key or the user's text
            raise LlmError("auth" if status in (401, 403) else "rate_limit" if status == 429
                           else "busy" if status >= 500 or status == 529 else "request", f"http {status}")
        except requests.RequestException:
            log.warning("anthropic request failed")
            raise LlmError("request")
        except (ValueError, AttributeError):
            raise LlmError("bad_reply")
        if not text:
            raise LlmError("bad_reply", "empty")
        return text


class OpenAICompatibleProvider(LLMProvider):
    name = "openai_compatible"
    supports_images = False  # text only here

    def is_configured(self) -> bool: return llm_client.is_configured()

    def generate(self, system, messages, max_tokens=900, temperature=0.3, image=None):
        try:
            return llm_client.chat([{"role": "system", "content": system}] + messages,
                                   temperature=temperature, max_tokens=max_tokens)
        except llm_client.LlmError as err:
            raise LlmError("not_configured" if "not configured" in str(err) else "request", str(err))


PROVIDERS = {"anthropic": AnthropicProvider, "openai_compatible": OpenAICompatibleProvider}


def get_provider() -> LLMProvider:
    name = (llm_client._secret("LLM_PROVIDER") or os.getenv("LLM_PROVIDER") or "anthropic").lower()
    return PROVIDERS.get(name, AnthropicProvider)()
