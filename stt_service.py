"""Speech to text for the farmer assistant, built on the existing Gnani client.

Default: the selected language with Gnani's default model (your original working request).
Optional 'detect my language': Prisma v3.0 with language_code=indic-auto (documented opt-in); if that request is
rejected, it retries with the selected language so the farmer is never stuck.
"""

import logging

import gnani_client as G
import languages as L

log = logging.getLogger("agrivoice.stt")
AUTO_MODEL, AUTO_CODE = "prisma-v3.0", "indic-auto"


def transcribe(data: bytes, filename: str, mime: str, lang: L.Language, auto_detect: bool = False, itn: bool = False):
    """Return (text, detected_language_code, error_tuple_or_None)."""
    if not L.is_usable(lang, "stt") and not auto_detect:
        return "", "", ("Request failed", "Please try again.")
    result = None
    if auto_detect:
        try:
            result = G.transcribe_audio(data, filename, mime, language_code=AUTO_CODE, apply_itn=itn, model=AUTO_MODEL)
        except G.GnaniError as err:
            log.info("auto-detect request failed (%s); retrying with the selected language", err.title)
    if result is None:
        if not L.is_usable(lang, "stt"):
            return "", "", ("Request failed", "Please try again.")
        try:
            result = G.transcribe_audio(data, filename, mime, language_code=lang.stt_code, apply_itn=itn)
        except G.GnaniError as err:
            return "", "", (err.title, err.detail)
    text = (G.extract_transcript(result) or "").strip()
    if not text:
        return "", "", ("No speech recognized", "Check that the audio is clear and spoken in the selected language.")
    return text, G.extract_detected_language(result), None
