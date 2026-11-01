"""Gnani speech client: Speech-to-Text and Text-to-Speech (REST).

Speech-to-Text request (unchanged from your working integration):
  - URL:        https://api.vachana.ai/stt/v3
  - Header:     X-API-Key-ID  (value read from GNANI_API_KEY)
  - Form data:  language_code  (plus format=transcribe only when apply_itn=True)
  - File field: audio_file
  - Timeout:    120 seconds
  - Parsing:    result.get("transcript", "")

Text-to-Speech (Gnani's API reference, https://docs.gnani.ai/api/TTS/tts-inference):
  POST https://api.vachana.ai/api/v1/tts/inference  -> raw audio bytes, same X-API-Key-ID header

Errors shown to people are short and plain. Technical detail (HTTP status, provider message) goes to the
server log only. The API key is never logged, printed or returned.
"""

import logging
import os
import threading

import requests
from dotenv import load_dotenv

load_dotenv()
log = logging.getLogger("agrivoice.gnani")

API_URL = "https://api.vachana.ai/stt/v3"
LANGUAGE_CODE = "te-IN"
TIMEOUT_SECONDS = 120
TTS_URL = "https://api.vachana.ai/api/v1/tts/inference"
TTS_TIMEOUT_SECONDS = 120
TTS_SPEED_RANGE = (0.85, 1.15)  # documented range

_local = threading.local()


def _session() -> requests.Session:
    """One HTTP session per thread: reuses the connection instead of reconnecting for every request."""
    if not hasattr(_local, "session"):
        _local.session = requests.Session()
    return _local.session


class GnaniError(Exception):
    """An error with a short title and a plain-language line for the screen."""

    def __init__(self, title: str, detail: str):
        super().__init__(title)
        self.title = title
        self.detail = detail


def get_api_key():
    return os.getenv("GNANI_API_KEY")


def _missing_key() -> GnaniError:
    log.error("GNANI_API_KEY is not set; speech requests cannot be sent.")
    return GnaniError("Service unavailable", "Please try again later.")


# ----------------------------------------------------------------------------- Speech-to-Text
def transcribe_audio(
    audio_bytes: bytes,
    filename: str = "sample.wav",
    mime_type: str = "audio/wav",
    language_code: str = LANGUAGE_CODE,
    apply_itn: bool = False,
    model: str | None = None,
) -> dict:
    """Send audio to the Gnani API and return the parsed JSON response."""
    api_key = get_api_key()
    if not api_key:
        raise _missing_key()

    form = {"language_code": language_code}
    if model:  # e.g. "prisma-v3.0" (opt-in, see docs.gnani.ai). Omitted = Gnani's default model, as before.
        form["model"] = model
    if apply_itn:
        form["format"] = "transcribe"

    response = None
    try:
        response = _session().post(
            API_URL,
            headers={"X-API-Key-ID": api_key},
            data=form,
            files={"audio_file": (filename, audio_bytes, mime_type)},
            timeout=TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        return response.json()

    except requests.Timeout:
        raise GnaniError("Request timed out", "Try a shorter clip.")
    except requests.ConnectionError:
        raise GnaniError("Connection problem", "Check your internet and try again.")
    except requests.HTTPError:
        raise GnaniError(*_http_message(response, "speech-to-text"))
    except ValueError:
        log.warning("speech-to-text: response was not valid JSON")
        raise GnaniError("Something went wrong", "Please try again.")
    except requests.RequestException:
        log.warning("speech-to-text: request failed", exc_info=False)
        raise GnaniError("Request failed", "Please try again.")


def extract_detected_language(result: dict) -> str:
    """Prisma v3.0 reports the language it heard (e.g. 'ta-IN'). Empty string when not reported."""
    return str(result.get("detected_language_code") or "")


def extract_transcript(result: dict) -> str:
    """Same parsing as the original script."""
    return result.get("transcript", "")


def _api_message(response) -> str:
    """Gnani error bodies look like {"success": false, "error": {"type": ..., "message": ...}}."""
    try:
        return str(response.json()["error"]["message"])[:300]
    except Exception:
        return ""


def _http_message(response, service):
    status = response.status_code if response is not None else "unknown"
    log.warning("%s: HTTP %s %s", service, status, _api_message(response) if response is not None else "")
    tts = service == "text-to-speech"
    if status in (401, 403):
        return ("Text to speech unavailable" if tts else "Speech to text unavailable", "Please try again later.")
    if status == 400:
        return (("Couldn't generate speech", "Check the text and voice, then try again.") if tts
                else ("Couldn't process this audio", "Check the format and length, then try again."))
    if status == 429:
        return ("Too many requests", "Wait a moment and try again.")
    if isinstance(status, int) and status >= 500:
        return ("Service busy", "Try again in a moment.")
    return ("Request failed", "Please try again.")


# ----------------------------------------------------------------------------- Text-to-Speech
_AUDIO_MAGIC = (b"RIFF", b"ID3", b"OggS", b"\xff\xfb", b"\xff\xf3", b"\xff\xf2")


def synthesize_speech(
    text: str,
    voice: str,
    model: str = "timbre-v2.5",
    language: str = "en-IN",
    speed: float = 1.0,
    container: str = "wav",
    sample_rate: int = 24000,
):
    """Generate speech. Returns (audio_bytes, content_type). Raises GnaniError on any problem.

    Body follows Gnani's documented schema. `container` is "wav" or "mp3".
    """
    api_key = get_api_key()
    if not api_key:
        raise _missing_key()
    if container not in ("wav", "mp3"):
        raise GnaniError("Unsupported format", "Choose WAV or MP3.")

    speed = max(TTS_SPEED_RANGE[0], min(TTS_SPEED_RANGE[1], float(speed)))
    audio_config = {"sample_rate": int(sample_rate), "num_channels": 1, "sample_width": 2, "container": container}
    if container == "wav":
        audio_config["encoding"] = "linear_pcm"
    else:
        audio_config["bitrate"] = "128k"

    body = {"text": text, "voice": voice, "model": model, "language": language, "speed": speed,
            "audio_config": audio_config}

    response = None
    try:
        response = _session().post(
            TTS_URL,
            headers={"X-API-Key-ID": api_key, "Content-Type": "application/json"},
            json=body,
            timeout=TTS_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
    except requests.Timeout:
        raise GnaniError("Request timed out", "Try shorter text.")
    except requests.ConnectionError:
        raise GnaniError("Connection problem", "Check your internet and try again.")
    except requests.HTTPError:
        raise GnaniError(*_http_message(response, "text-to-speech"))
    except requests.RequestException:
        log.warning("text-to-speech: request failed")
        raise GnaniError("Request failed", "Please try again.")

    audio = response.content or b""
    content_type = (response.headers.get("Content-Type") or "").split(";")[0].strip().lower()
    if not audio or content_type.startswith("application/json") or not (
        content_type.startswith("audio/") or audio[:4] in _AUDIO_MAGIC or audio[:2] == b"\xff\xfb"
    ):
        log.warning("text-to-speech: response was not audio (%s)", _api_message(response))
        raise GnaniError("No audio generated", "Please try again.")
    if not content_type.startswith("audio/"):
        content_type = "audio/mpeg" if container == "mp3" else "audio/wav"
    return audio, content_type
