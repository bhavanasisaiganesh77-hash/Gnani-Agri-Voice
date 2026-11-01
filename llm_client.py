"""Optional AI model client for the agricultural assistant.

Supports OpenAI-compatible APIs such as Google Gemini.
Settings are loaded from .env or Streamlit secrets.
"""

import logging
import os
import threading

import requests
from dotenv import load_dotenv

load_dotenv()

log = logging.getLogger("agrivoice.llm")

TIMEOUT_SECONDS = 90
_local = threading.local()


class LlmError(Exception):
    """Safe error raised when the AI model request fails."""
    pass


def _session() -> requests.Session:
    if not hasattr(_local, "session"):
        _local.session = requests.Session()
    return _local.session


def _secret(name: str) -> str:
    """Read settings from environment or Streamlit secrets."""
    value = os.getenv(name)

    if not value:
        try:
            import streamlit as st
            value = st.secrets.get(name)
        except Exception:
            value = None

    return (value or "").strip()


def _settings():
    key = _secret("LLM_API_KEY")
    base = _secret("LLM_BASE_URL").rstrip("/")
    model = _secret("LLM_MODEL")

    return key, base, model


def is_configured() -> bool:
    """Check whether all required settings exist."""
    return all(_settings())


def chat(
    messages: list,
    temperature: float = 0.3,
    max_tokens: int = 600
) -> str:
    """Send messages to the configured AI model."""

    key, base, model = _settings()

    if not key or not base or not model:
        raise LlmError("Gemini settings are incomplete. Check your .env file.")

    if not base.startswith(("https://", "http://")):
        raise LlmError("LLM_BASE_URL must start with https://")

    response = None

    try:
        response = _session().post(
            f"{base}/chat/completions",
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json"
            },
            json={
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens
            },
            timeout=TIMEOUT_SECONDS
        )

        response.raise_for_status()

        data = response.json()

        text = (
            data["choices"][0]["message"]["content"] or ""
        ).strip()

    except requests.HTTPError:
        status = response.status_code if response is not None else "unknown"

        detail = ""

        if response is not None:
            try:
                error_data = response.json()
                error = error_data.get("error", {})

                if isinstance(error, dict):
                    detail = error.get("message", "")

            except (ValueError, AttributeError):
                detail = ""

        # Avoid printing API keys or authorization headers.
        detail = str(detail)[:300]

        log.error(
            "Gemini API HTTP error | status=%s | detail=%s",
            status,
            detail or "No additional details"
        )

        if status == 503:
            raise LlmError(
                "Gemini service is temporarily unavailable (HTTP 503)."
            )

        elif status == 429:
            raise LlmError(
                "Gemini API quota or rate limit exceeded (HTTP 429)."
            )

        elif status == 400:
            raise LlmError(
                f"Gemini rejected the request (HTTP 400): {detail}"
            )

        elif status in (401, 403):
            raise LlmError(
                f"Gemini authentication or permission error (HTTP {status})."
            )

        else:
            raise LlmError(
                f"Gemini API returned HTTP {status}: {detail}"
            )

    except requests.Timeout:
        log.error("Gemini API request timed out.")
        raise LlmError("Gemini request timed out.")

    except requests.RequestException as err:
        log.error("Gemini network request failed: %s", type(err).__name__)
        raise LlmError("Unable to connect to Gemini.")

    except (ValueError, KeyError, IndexError, TypeError):
        log.error("Gemini returned an unexpected response format.")
        raise LlmError("Gemini returned an invalid response.")

    if not text:
        raise LlmError("Gemini returned an empty response.")

    return text