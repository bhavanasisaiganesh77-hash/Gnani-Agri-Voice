"""Central language configuration for GNANI AGRI VOICE.

Used by Speech-to-Text and Text-to-Speech, so a language is described once.

SOURCES (official Gnani docs, https://docs.gnani.ai):
  - STT REST  /api/STT/speech-to-text : bn-IN en-IN gu-IN hi-IN kn-IN ml-IN mr-IN pa-IN ta-IN te-IN
  - TTS REST  /api/TTS/tts-inference  : the same ten, plus `hi-en` (Hinglish) and `auto`

Each language has TWO separate answers:
  * stt_status / stt_code : can Gnani transcribe it?
  * tts_status / tts_code : can Gnani speak it?

A language with code=None can never be sent to an API.

TO ADD A LANGUAGE LATER: when Gnani publishes codes for it, fill in `stt_code` / `tts_code` and
set the status to SUPPORTED. Nothing else in the app needs to change.
"""

from dataclasses import dataclass

SUPPORTED = "supported"
EXPERIMENTAL = "experimental"
UNSUPPORTED = "unsupported"


@dataclass(frozen=True)
class Language:
    id: str
    name: str
    native: str
    stt_code: str | None = None
    stt_status: str = UNSUPPORTED
    tts_code: str | None = None
    tts_status: str = UNSUPPORTED
    note: str = ""
    eighth_schedule: bool = True

_NO_CODE = "Gnani has not published a speech-to-text or text-to-speech code for this language."
_NOT_IN_TABLE = ("Mentioned by a third-party page or Gnani's marketing, but absent from Gnani's official "
                 "API language tables, so no code is used.")


def _ok(id, name, native, code, note=""):
    return Language(id, name, native, code, SUPPORTED, code, SUPPORTED, note)


_ALL = [
    # --- The 22 languages of the Eighth Schedule ---------------------------------------
    Language("assamese", "Assamese", "অসমীয়া", note=_NOT_IN_TABLE),
    _ok("bengali", "Bengali", "বাংলা", "bn-IN"),
    Language("bodo", "Bodo", "बड़ो", note=_NO_CODE),
    Language("dogri", "Dogri", "डोगरी", note=_NO_CODE),
    _ok("gujarati", "Gujarati", "ગુજરાતી", "gu-IN",
        "Speech-to-text is not offered on Gnani's Batch API for this language, but works on the REST API this app uses."),
    _ok("hindi", "Hindi", "हिन्दी", "hi-IN"),
    _ok("kannada", "Kannada", "ಕನ್ನಡ", "kn-IN"),
    Language("kashmiri", "Kashmiri", "کٲشُر", note=_NO_CODE),
    Language("konkani", "Konkani", "कोंकणी", note=_NO_CODE),
    Language("maithili", "Maithili", "मैथिली", note=_NO_CODE),
    _ok("malayalam", "Malayalam", "മലയാളം", "ml-IN"),
    Language("manipuri", "Manipuri (Meitei)", "ꯃꯩꯇꯩꯂꯣꯟ", note=_NO_CODE),
    _ok("marathi", "Marathi", "मराठी", "mr-IN"),
    Language("nepali", "Nepali", "नेपाली", note=_NO_CODE),
    Language("odia", "Odia", "ଓଡ଼ିଆ", note=_NOT_IN_TABLE),
    _ok("punjabi", "Punjabi", "ਪੰਜਾਬੀ", "pa-IN"),
    Language("sanskrit", "Sanskrit", "संस्कृतम्", note=_NO_CODE),
    Language("santali", "Santali", "ᱥᱟᱱᱛᱟᱲᱤ", note=_NO_CODE),
    Language("sindhi", "Sindhi", "سنڌي", note=_NO_CODE),
    _ok("tamil", "Tamil", "தமிழ்", "ta-IN"),
    _ok("telugu", "Telugu", "తెలుగు", "te-IN"),
    Language("urdu", "Urdu", "اردو", note=_NO_CODE),
    # --- Outside the Eighth Schedule / code-mixed --------------------------------------
    Language("english", "English", "English", "en-IN", SUPPORTED, "en-IN", SUPPORTED,
             "Speech-to-text accepts English-Hindi mixed audio and writes English (Latin script).",
             eighth_schedule=False),
    Language("hindi_english", "Hindi + English", "Hindi + English",
             "en-IN,hi-IN", EXPERIMENTAL, "hi-en", SUPPORTED,
             "Text-to-speech code 'hi-en' (Hinglish) is in Gnani's TTS table. For speech-to-text, 'en-IN,hi-IN' "
             "appears in Gnani's SDK README but not in the REST enum, so confirm it on your account.",
             eighth_schedule=False),
]

_ORDER = {SUPPORTED: 0, EXPERIMENTAL: 1, UNSUPPORTED: 2}


def _sort_key(capability):
    def key(l):
        return (_ORDER[status(l, capability)], l.name)
    return key


def status(lang: Language, capability: str) -> str:
    return {"stt": lang.stt_status, "tts": lang.tts_status}[capability]


def code(lang: Language, capability: str):
    """The exact API language code for this capability (None if there is none)."""
    return {"stt": lang.stt_code, "tts": lang.tts_code}[capability]


DEFAULT_LANGUAGE_ID = "telugu"  # the language your original script used (te-IN)
DEFAULT_UI_LANGUAGE_ID = "english"  # shown to visitors who have not chosen a language yet

# ISO 639-1 codes. A language's interface is translated when locales/<iso>.json exists.
ISO = {"english": "en", "telugu": "te", "tamil": "ta", "hindi": "hi", "kannada": "kn", "malayalam": "ml",
       "bengali": "bn", "marathi": "mr", "gujarati": "gu", "punjabi": "pa", "odia": "or", "assamese": "as",
       "urdu": "ur"}
RTL = {"urdu"}

# The 13 languages offered in the app, in the order farmers expect to see them.
APP_LANGUAGE_IDS = ["telugu", "tamil", "hindi", "kannada", "malayalam", "bengali", "marathi", "gujarati",
                    "punjabi", "odia", "assamese", "urdu", "english"]


def iso_code(language_id: str):
    return ISO.get(language_id)


def is_rtl(language_id: str) -> bool:
    return language_id in RTL


def app_languages():
    return [get_language(i) for i in APP_LANGUAGE_IDS]


def voice_ready(lang: "Language") -> bool:
    """True when BOTH speech-to-text and text-to-speech work for this language."""
    return is_usable(lang, "stt") and is_usable(lang, "tts")


def app_label(lang: "Language", voice_note: str = "") -> str:
    """Selector text: the language in its own script (plus English name when different), with a clear voice marker."""
    base = lang.native if lang.native == lang.name else f"{lang.native} · {lang.name}"
    return f"{base} ({voice_note})" if voice_note and not voice_ready(lang) else base
_BY_ID = {l.id: l for l in _ALL}

# All languages for a capability, usable ones first (alphabetical), then the rest.
def languages_for(capability: str):
    return sorted(_ALL, key=_sort_key(capability))


LANGUAGES = languages_for("stt")


def get_language(language_id: str) -> Language:
    return _BY_ID.get(language_id) or _BY_ID[DEFAULT_LANGUAGE_ID]


def is_usable(lang: Language, capability: str) -> bool:
    return code(lang, capability) is not None and status(lang, capability) in (SUPPORTED, EXPERIMENTAL)


def usable_languages(capability: str):
    return [l for l in languages_for(capability) if is_usable(l, capability)]


def label(lang: Language, capability: str) -> str:
    """Dropdown text. Unavailable languages stay visible but are clearly marked."""
    base = f"{lang.name} ({lang.native})" if lang.native != lang.name else lang.name
    s = status(lang, capability)
    if s == EXPERIMENTAL:
        return f"{base} (experimental)"
    if s == UNSUPPORTED:
        return f"{base} (not available)"
    return base


def coverage(capability: str = "stt"):
    """(fully supported Eighth Schedule languages, total Eighth Schedule languages)."""
    schedule = [l for l in _ALL if l.eighth_schedule]
    return sum(1 for l in schedule if status(l, capability) == SUPPORTED), len(schedule)


STATUS_TEXT = {SUPPORTED: "Supported", EXPERIMENTAL: "Experimental", UNSUPPORTED: "Not supported yet"}
