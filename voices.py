"""Text-to-Speech models and voices, exactly as listed in Gnani's official documentation.

SOURCES:
  - Model and voice names: https://docs.gnani.ai/api/TTS/tts-inference (OpenAPI schema)
  - timbre-v2.5 voices (42): Gnani's Python SDK `gnani-vachana` (TIMBRE_V25_VOICES), grouped by the
    language each voice is built for, as published in Gnani's Pipecat integration page.
  - timbre-v3.0 voices (13): the OpenAPI schema above. Each speaks all supported languages.

Never add a voice here unless it is in those sources. Gnani says a voice only works with its own model.
"""

MODELS = {
    "timbre-v2.5": "Timbre v2.5 (42 voices)",
    "timbre-v3.0": "Timbre v3.0 (13 voices, newer)",
}
DEFAULT_MODEL = "timbre-v2.5"

# timbre-v2.5: the language group each voice is built for.
V25_BY_GROUP = {
    "Hindi": ["Nalini", "Bhavna", "Yashvi", "Urmila", "Jwala", "Chitra", "Ambuja", "Deepak", "Roopesh", "Vikrant", "Hemraj", "Jalaj", "Omkar"],
    "English": ["Kaveri", "Trupti", "Devika", "Pranav", "Shlok", "Girish"],
    "Tamil": ["Asmita", "Trisha", "Brinda", "Vedika", "Noopur"],
    "Telugu": ["Suhana", "Lehara", "Lavanya", "Yukti", "Varuni"],
    "Kannada": ["Saanvi", "Kavin"],
    "Malayalam": ["Reshma", "Riyaan"],
    "Marathi": ["Zahira", "Ishaan"],
    "Bengali": ["Kirra", "Dhruva"],
    "Gujarati": ["Falak", "Veera"],
    "Punjabi": ["Mehuli", "Zayan"],
    "Hinglish": ["Poorvi"],
}

V30_VOICES = ["Avinash", "Shivani", "Lakshmi", "Kalpana", "Shubham", "Prakash", "Devansh",
              "Yashraj", "Chetana", "Vasudha", "Riyaa", "Tarika", "Harshad"]

# Our language ids -> the voice group used to suggest voices.
GROUP_FOR_LANGUAGE = {
    "hindi": "Hindi", "english": "English", "tamil": "Tamil", "telugu": "Telugu", "kannada": "Kannada",
    "malayalam": "Malayalam", "marathi": "Marathi", "bengali": "Bengali", "gujarati": "Gujarati",
    "punjabi": "Punjabi", "hindi_english": "Hinglish",
}


def voices_for(model: str, language_id: str):
    """List of (voice, hint). Voices built for the chosen language come first."""
    if model == "timbre-v3.0":
        return [(v, "speaks every supported language") for v in V30_VOICES]
    group = GROUP_FOR_LANGUAGE.get(language_id)
    preferred = [(v, f"built for {group}") for v in V25_BY_GROUP.get(group, [])]
    others = [(v, f"built for {g}") for g, vs in V25_BY_GROUP.items() if g != group for v in vs]
    return preferred + others


def default_voice(model: str, language_id: str) -> str:
    return voices_for(model, language_id)[0][0]


def all_voices(model: str):
    if model == "timbre-v3.0":
        return list(V30_VOICES)
    return [v for vs in V25_BY_GROUP.values() for v in vs]
