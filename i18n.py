"""Central localization for GNANI AGRI VOICE.

* One JSON file per language in locales/ (en.json is the source of truth).
* t("key", name="Ravi")       -> text in the current language (falls back to English, then the key).
* m("English message")        -> translates known English messages that come from the database, the Gnani client
                                 and the audio checks (stored under "msg" in each locale file).
* To add a language: copy locales/en.json to locales/<iso>.json, translate the values, and add the
  language's iso code in languages.ISO. Nothing else changes.

The current language lives in st.session_state["lang_id"] (set at login from the user's saved preference).
"""

import json
import logging
import re
from functools import lru_cache
from pathlib import Path

import languages as L

log = logging.getLogger("agrivoice.i18n")
LOCALE_DIR = Path(__file__).resolve().parent / "locales"
FALLBACK = "en"
_PLACEHOLDER = re.compile(r"\{(\w+)\}")


@lru_cache(maxsize=None)
def _load(iso: str) -> dict:
    path = LOCALE_DIR / f"{iso}.json"
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        log.warning("locale file %s is missing or invalid", path.name)
        return {}


def available_isos() -> list:
    return sorted(p.stem for p in LOCALE_DIR.glob("*.json"))


def has_ui(lang_id: str) -> bool:
    """True when the interface itself is translated into this language."""
    iso = L.iso_code(lang_id)
    return bool(iso) and (LOCALE_DIR / f"{iso}.json").is_file()


def current_lang_id() -> str:
    try:
        import streamlit as st
        return st.session_state.get("lang_id") or L.DEFAULT_UI_LANGUAGE_ID
    except Exception:
        return L.DEFAULT_UI_LANGUAGE_ID


def ui_iso(lang_id: str | None = None) -> str:
    lang_id = lang_id or current_lang_id()
    return L.iso_code(lang_id) if has_ui(lang_id) else FALLBACK


def t(key: str, lang_id: str | None = None, **values) -> str:
    iso = ui_iso(lang_id)
    text = _load(iso).get(key)
    if text is None:
        text = _load(FALLBACK).get(key)
    if text is None:
        log.warning("missing translation key: %s", key)
        return key
    if values:
        try:
            return text.format(**values)
        except (KeyError, IndexError, ValueError):
            log.warning("bad placeholders in %s (%s)", key, iso)
    return text


@lru_cache(maxsize=None)
def _patterns(iso: str):
    """Compile 'msg' entries that contain {placeholders} into regular expressions."""
    out = []
    for source, target in _load(iso).get("msg", {}).items():
        if "{" in source:
            rx = re.escape(source)
            rx = _PLACEHOLDER.sub(lambda mo: f"(?P<{mo.group(1)}>.+?)", rx.replace(r"\{", "{").replace(r"\}", "}"))
            out.append((re.compile(f"^{rx}$"), target))
    return out


def m(message: str, lang_id: str | None = None) -> str:
    """Translate a known English message; anything unknown is returned unchanged."""
    if not message:
        return message
    iso = ui_iso(lang_id)
    if iso == FALLBACK:
        return message
    table = _load(iso).get("msg", {})
    if message in table:
        return table[message]
    for rx, target in _patterns(iso):
        match = rx.match(message)
        if match:
            try:
                return target.format(**match.groupdict())
            except (KeyError, ValueError):
                break
    return message


def validate_locales() -> list:
    """Return a list of problems (used by the tests): missing keys and mismatched placeholders."""
    problems = []
    base = _load(FALLBACK)
    base_keys = {k for k in base if k != "msg"}
    for iso in available_isos():
        if iso == FALLBACK:
            continue
        data = _load(iso)
        for k in sorted(base_keys - set(data)):
            problems.append(f"{iso}: missing key {k}")
        for k in sorted(set(data) - base_keys - {"msg"}):
            problems.append(f"{iso}: unknown key {k}")
        for k in base_keys & set(data):
            if set(_PLACEHOLDER.findall(base[k])) != set(_PLACEHOLDER.findall(data[k])):
                problems.append(f"{iso}: placeholder mismatch in {k}")
    return problems
