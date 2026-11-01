"""Government schemes from data/schemes.json, with the date each entry was last checked against its sources.

An entry with last_verified = null is shown as 'not yet checked' and carries no numbers. To update an entry, check the
official website, edit the JSON, and set last_verified to that day. The app never invents scheme details.
"""
import json
from pathlib import Path

DATA = Path(__file__).resolve().parent / "data" / "schemes.json"


def load() -> list:
    try:
        return json.loads(DATA.read_text(encoding="utf-8"))["schemes"]
    except (OSError, ValueError, KeyError):
        return []


def get(scheme_id: str):
    return next((s for s in load() if s["id"] == scheme_id), None)
