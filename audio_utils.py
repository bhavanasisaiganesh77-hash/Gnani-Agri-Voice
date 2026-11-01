"""Client-side checks run before audio is sent, so users get clear errors early.

Limits come from Gnani REST docs (docs.gnani.ai, Prisma v3.0 page): WAV, MP3, OGG, FLAC, AAC, M4A; 30 seconds maximum
(shorter is better). MAX_BYTES is this app's own safety cap, not a Gnani limit.
"""

import io
import wave

ALLOWED_EXTENSIONS = ["wav", "mp3", "ogg", "flac", "aac", "m4a"]
MIME_TYPES = {
    "wav": "audio/wav",
    "mp3": "audio/mpeg",
    "ogg": "audio/ogg",
    "flac": "audio/flac",
    "aac": "audio/aac",
    "m4a": "audio/mp4",
}
MAX_SECONDS = 30
IDEAL_SECONDS = 20
MAX_BYTES = 8 * 1024 * 1024


def get_duration(data: bytes, extension: str):
    """Duration in seconds, or None when it cannot be read (the API will still validate)."""
    try:
        if extension == "wav":
            with wave.open(io.BytesIO(data)) as w:
                return w.getnframes() / float(w.getframerate())
    except Exception:
        pass
    try:
        import mutagen

        info = mutagen.File(io.BytesIO(data))
        if info is not None and info.info is not None and info.info.length:
            return float(info.info.length)
    except Exception:
        pass
    return None


def validate_audio(filename: str, data: bytes):
    """Return (error or None, duration or None, mime type)."""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        return (("Unsupported file type", "That file type is not supported. Use WAV, MP3, OGG, FLAC, AAC or M4A."),
            None,
            "",
        )
    if not data:
        return (("The file is empty", "Choose a different file or record again."), None, "")
    if len(data) > MAX_BYTES:
        return (
            ("The file is too large", "Files up to 8 MB are accepted."),
            None,
            "",
        )
    duration = get_duration(data, ext)
    if duration is not None and duration > MAX_SECONDS:
        return (
            ("The clip is too long", "Please keep the recording under 30 seconds."),
            duration,
            "",
        )
    return None, duration, MIME_TYPES[ext]


def fmt_duration(seconds: float) -> str:
    seconds = int(round(seconds))
    return f"{seconds // 60}:{seconds % 60:02d}"


def fmt_size(n: int) -> str:
    return f"{n / 1024:.0f} KB" if n < 1024 * 1024 else f"{n / (1024 * 1024):.1f} MB"
