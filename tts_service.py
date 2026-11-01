"""Spoken answers through Gnani Timbre.

Long answers are split into chunks and combined into one WAV clip.
Keeps the existing Gnani synthesis integration and voice configuration.
"""

import io
import logging
import re
import wave

import gnani_client as G
import languages as L
import voices

log = logging.getLogger("agrivoice.tts")

CHUNK_CHARS = 800
MAX_CHUNKS = 4
MODEL = voices.DEFAULT_MODEL


def plain_text(markdown: str) -> str:
    """Remove Markdown formatting before sending text to speech."""
    text = re.sub(r"```.*?```", " ", markdown or "", flags=re.S)
    text = re.sub(r"[*_#>`~|]+", "", text)
    text = re.sub(r"^\s*[-•]\s+", "", text, flags=re.M)
    return re.sub(
        r"[ \t]+",
        " ",
        re.sub(r"\n{2,}", "\n", text)
    ).strip()


def split_text(text: str, size: int = CHUNK_CHARS) -> list:
    """Split text into chunks without unnecessarily breaking sentences."""
    sentences = re.split(r"(?<=[.!?।॥؟])\s+|\n+", text)

    chunks = []
    current = ""

    for sentence in sentences:
        sentence = sentence.strip()

        if not sentence:
            continue

        while len(sentence) > size:
            cut = sentence.rfind(" ", 0, size)

            if cut <= 0:
                cut = size

            chunks.append(sentence[:cut].strip())
            sentence = sentence[cut:].strip()

        if current and len(current) + len(sentence) + 1 > size:
            chunks.append(current)
            current = sentence
        else:
            current = f"{current} {sentence}".strip()

    if current:
        chunks.append(current)

    return chunks


def join_wavs(parts: list) -> bytes:
    """Combine compatible WAV files without rewriting their WAV header."""

    if not parts:
        raise G.GnaniError(
            "No audio generated",
            "Please try again."
        )

    if len(parts) == 1:
        return parts[0]

    frames = []
    reference_params = None

    try:
        for raw in parts:
            with wave.open(io.BytesIO(raw), "rb") as wav:
                params = (
                    wav.getnchannels(),
                    wav.getsampwidth(),
                    wav.getframerate(),
                    wav.getcomptype()
                )

                if reference_params is None:
                    reference_params = params
                elif params != reference_params:
                    raise G.GnaniError(
                        "Audio format mismatch",
                        "Please try again."
                    )

                frames.append(wav.readframes(wav.getnframes()))

        # Construct the WAV file once, after collecting all audio frames.
        output = io.BytesIO()

        with wave.open(output, "wb") as combined:
            combined.setnchannels(reference_params[0])
            combined.setsampwidth(reference_params[1])
            combined.setframerate(reference_params[2])
            combined.setcomptype(reference_params[3], "not compressed")

            for frame_data in frames:
                combined.writeframesraw(frame_data)

        return output.getvalue()

    except (wave.Error, EOFError, OSError) as err:
        log.exception("Could not combine WAV audio: %s", err)
        raise G.GnaniError(
            "No audio generated",
            "Please try again."
        )


def speak(text: str, lang: L.Language, voice: str | None = None):
    """Generate one WAV response using Gnani Timbre."""

    if not L.is_usable(lang, "tts"):
        raise G.GnaniError(
            "Text to speech unavailable",
            "Please try again later."
        )

    chunks = split_text(plain_text(text))

    if not chunks:
        raise G.GnaniError(
            "Couldn't generate speech",
            "Check the text and voice, then try again."
        )

    # Limit the number of requests to control audio size and API usage.
    selected_chunks = chunks[:MAX_CHUNKS]

    voice = voice or voices.default_voice(MODEL, lang.id)

    parts = []

    for index, chunk in enumerate(selected_chunks, start=1):
        try:
            audio, mime = G.synthesize_speech(
                chunk,
                voice=voice,
                model=MODEL,
                language=lang.tts_code,
                container="wav",
                sample_rate=24000
            )

            if not audio:
                raise G.GnaniError(
                    "No audio generated",
                    "Please try again."
                )

            # Validate the WAV returned by Gnani.
            with wave.open(io.BytesIO(audio), "rb") as wav:
                log.info(
                    "Gnani TTS chunk %d: size=%d bytes, channels=%d, "
                    "sample_width=%d, sample_rate=%d, frames=%d",
                    index,
                    len(audio),
                    wav.getnchannels(),
                    wav.getsampwidth(),
                    wav.getframerate(),
                    wav.getnframes()
                )

            parts.append(audio)

        except (wave.Error, EOFError, OSError) as err:
            log.exception("Invalid Gnani WAV response: %s", err)
            raise G.GnaniError(
                "Invalid audio response",
                "Please try again."
            )

    combined_audio = join_wavs(parts)

    # True means the complete answer was spoken.
    complete = len(chunks) <= MAX_CHUNKS

    return combined_audio, complete