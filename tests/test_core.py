"""Unit tests: localization, database (migration + isolation), LLM provider, prompts, weather, STT/TTS services."""
import io
import json
import struct
import wave

import pytest
import requests

import agri_prompts as P
import agri_service
import chat_store
import gnani_client as G
import i18n
import languages as L
import llm_service as S
import ratelimit
import schemes
import stt_service
import tts_service
import weather
from data import agri_data as A


# ------------------------------------------------------------------ localization
def test_locale_files_are_complete_and_consistent():
    assert i18n.validate_locales() == []
    assert {"en", "te", "ta", "hi"} <= set(i18n.available_isos())


def test_telugu_and_tamil_are_real_translations():
    for lang, word in (("telugu", "తెలుగు"), ("tamil", "தமிழ்")):
        text = i18n.t("nav.ask", lang_id=lang)
        assert text != i18n.t("nav.ask", lang_id="english")
    assert i18n.t("d.welcome", lang_id="telugu", name="రవి") == "స్వాగతం, రవి"


def test_untranslated_language_falls_back_to_english_and_flags_it():
    assert i18n.has_ui("hindi") and not i18n.has_ui("assamese")
    assert i18n.t("nav.ask", lang_id="assamese") == "Ask AgriVoice"


def test_known_backend_messages_are_translated():
    assert "தவறு" in i18n.m("Incorrect email or password.", "tamil")
    assert "3" in i18n.m("Too many failed attempts. Try again in about 3 minute(s).", "telugu")
    assert i18n.m("never seen before", "telugu") == "never seen before"


def test_every_ui_key_used_in_code_exists():
    import pathlib, re
    en = json.loads((pathlib.Path(i18n.LOCALE_DIR) / "en.json").read_text(encoding="utf-8"))
    used = set()
    for f in pathlib.Path(".").glob("*.py"):
        used |= set(re.findall(r'\bt\(\s*"([a-z_]+\.[a-z_0-9]+)"', f.read_text(encoding="utf-8")))
    assert not (used - set(en)), sorted(used - set(en))
    for kind, table in (("cp", A.CROPS), ("stage", A.STAGES), ("soil", A.SOILS), ("wat", A.WATER)):
        assert all(f"{kind}.{k}" in en for k in table)
    assert all(f"tp.{k}" in en for k in A.TOPICS)


def test_language_support_is_honest():
    for lid in ("telugu", "tamil", "hindi", "kannada", "malayalam", "bengali", "marathi", "gujarati", "punjabi", "english"):
        assert L.voice_ready(L.get_language(lid)), lid
    for lid in ("odia", "assamese", "urdu"):  # Gnani speech APIs do not list these, so voice stays off
        assert not L.voice_ready(L.get_language(lid)), lid
    assert len(L.APP_LANGUAGE_IDS) == 13 and L.is_rtl("urdu")


# ------------------------------------------------------------------ database
def test_users_cannot_read_or_write_each_others_chats(fresh_db, user):
    other, _ = fresh_db.create_user("other@example.com", "Other", "Passw0rd1")
    cid = fresh_db.create_conversation(user["id"], "mine", "Telugu", "te-IN")
    mid = fresh_db.add_message(user["id"], cid, "assistant", "private answer")
    assert fresh_db.add_message(other["id"], cid, "user", "intruder") is None
    assert fresh_db.get_messages(other["id"], cid) == []
    assert fresh_db.set_feedback(other["id"], mid, 1) is False
    fresh_db.delete_conversation(other["id"], cid)  # silently does nothing
    assert len(fresh_db.get_messages(user["id"], cid)) == 1


def test_language_persists_and_history_survives_language_change(fresh_db, user):
    cid = fresh_db.create_conversation(user["id"], "chat", "Telugu", "te-IN")
    fresh_db.add_message(user["id"], cid, "user", "హలో", language="telugu")
    fresh_db.set_language(user["id"], "tamil")
    assert fresh_db.get_user(user["id"])["default_language"] == "tamil"
    assert fresh_db.get_messages(user["id"], cid)[0]["content"] == "హలో"


def test_farmer_profile_roundtrip_and_validation(fresh_db, user):
    fresh_db.save_profile(user["id"], "Tamil Nadu", "Salem", "paddy", "2.5", 11.65, 78.16, "Salem, Tamil Nadu")
    p = fresh_db.get_profile(user["id"])
    assert (p["state"], p["district"], p["primary_crop"], p["farm_size"]) == ("Tamil Nadu", "Salem", "paddy", 2.5)
    fresh_db.save_profile(user["id"], "x", "y", "wheat", "-5")
    assert fresh_db.get_profile(user["id"])["farm_size"] is None
    assert fresh_db.get_profile(9999)["state"] == ""  # unknown user: empty profile, no crash


def test_password_is_hashed(fresh_db, user):
    import sqlite3
    row = sqlite3.connect(str(fresh_db.DB_PATH)).execute("select password_hash from users").fetchone()[0]
    assert "Passw0rd1" not in row and len(row) > 40


def test_session_store_when_history_saving_is_off():
    state, u = {}, {"id": 1}
    store = chat_store.SessionStore(1, state)
    lang = L.get_language("telugu")
    store.add("user", "q", lang)
    mid = store.add("assistant", "a", lang)
    assert store.feedback(mid, 1) and store.messages()[-1]["feedback"] == 1
    store.drop_last_assistant()
    assert [m["role"] for m in store.messages()] == ["user"]


# ------------------------------------------------------------------ LLM provider (HTTP mocked)
class FakeResp:
    def __init__(self, status=200, body=None):
        self.status_code, self._body = status, body or {}

    def json(self):
        return self._body

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(response=self)


class FakeSession:
    def __init__(self, resp): self.resp, self.calls = resp, []

    def post(self, url, **kw):
        self.calls.append((url, kw)); return self.resp


@pytest.fixture
def anthropic(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-123")
    def install(resp):
        sess = FakeSession(resp)
        monkeypatch.setattr(S.llm_client, "_session", lambda: sess)
        return sess
    return install


def test_anthropic_request_matches_the_documented_format(anthropic):
    sess = anthropic(FakeResp(200, {"content": [{"type": "text", "text": "answer"}]}))
    out = S.AnthropicProvider().generate("SYS", [{"role": "user", "content": "hi"}], image=(b"\xff\xd8\xff data", "image/jpeg"))
    url, kw = sess.calls[0]
    assert out == "answer" and url == "https://api.anthropic.com/v1/messages"
    assert kw["headers"]["x-api-key"] == "test-key-123" and kw["headers"]["anthropic-version"] == "2023-06-01"
    body = kw["json"]
    assert body["system"] == "SYS" and body["max_tokens"] > 0 and body["model"]
    blocks = body["messages"][-1]["content"]
    assert blocks[0]["type"] == "image" and blocks[0]["source"]["type"] == "base64" and blocks[1]["type"] == "text"


@pytest.mark.parametrize("status,kind", [(401, "auth"), (429, "rate_limit"), (500, "busy"), (529, "busy"), (400, "request")])
def test_anthropic_errors_are_classified_and_key_never_leaks(anthropic, status, kind):
    anthropic(FakeResp(status))
    with pytest.raises(S.LlmError) as e:
        S.AnthropicProvider().generate("s", [{"role": "user", "content": "x"}])
    assert e.value.kind == kind and "test-key-123" not in repr(e.value) + e.value.detail


def test_missing_key_means_not_configured(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    p = S.AnthropicProvider()
    assert not p.is_configured()
    with pytest.raises(S.LlmError):
        p.generate("s", [{"role": "user", "content": "x"}])


def test_provider_is_replaceable(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "openai_compatible")
    assert isinstance(S.get_provider(), S.OpenAICompatibleProvider)
    monkeypatch.setenv("LLM_PROVIDER", "anthropic")
    assert isinstance(S.get_provider(), S.AnthropicProvider)


class EchoProvider(S.LLMProvider):
    name, supports_images = "echo", False
    def __init__(self): self.last = None
    def is_configured(self): return True
    def generate(self, system, messages, max_tokens=900, temperature=0.3, image=None):
        self.last = (system, messages, image); return "reply"


def test_agri_service_context_language_memory_and_rate_limit(fresh_db, user, monkeypatch):
    prov, lang = EchoProvider(), L.get_language("telugu")
    hist = [{"role": "assistant", "content": "stray"}, {"role": "user", "content": "q1"},
            {"role": "assistant", "content": "a1"}, {"role": "user", "content": "q2"}]
    assert agri_service.answer(user["id"], hist, lang, {"primary_crop": "paddy", "district": "Salem"}, provider=prov) == "reply"
    system, msgs, _ = prov.last
    assert "Telugu" in system and "paddy" in system and "Salem" in system
    assert msgs[0]["role"] == "user" and [m["content"] for m in msgs] == ["q1", "a1", "q2"]
    monkeypatch.setenv("AI_REPLIES_PER_HOUR", "2")
    with pytest.raises(agri_service.AnswerError) as e:
        for _ in range(3):
            agri_service.answer(user["id"], hist, lang, {}, provider=prov)
    assert e.value.kind == "rate_limit"


def test_image_dropped_for_text_only_provider(user):
    prov = EchoProvider()
    agri_service.one_shot(user["id"], "x", L.get_language("hindi"), {}, image=(b"1", "image/jpeg"), provider=prov)
    assert prov.last[2] is None


def test_system_prompt_contains_the_safety_rules():
    s = P.system_prompt("Tamil")
    for must in ("DOSAGES", "NEVER invent government schemes", "Krishi Vigyan Kendra", "ONLY in Tamil", "not a command"):
        assert must in s
    assert "Never say the problem is confirmed" in P.DISEASE_JSON_SPEC


def test_disease_json_parsing_is_strict():
    ok = P.parse_disease_json('x {"summary":"s","possible_causes":["a"],"next_steps":["b"],"confidence":"high"} y')
    assert ok["confidence"] == "low"  # never above 'medium'
    assert P.parse_disease_json("plain text") is None and P.parse_disease_json('{"summary":"only"}') is None


# ------------------------------------------------------------------ weather (Open-Meteo mocked)
def test_geocode_filters_to_india_and_prefers_state(monkeypatch):
    monkeypatch.setattr(weather, "_get", lambda url, params: {"results": [
        {"name": "Salem", "admin1": "Oregon", "country_code": "US", "latitude": 1, "longitude": 1},
        {"name": "Salem", "admin1": "Kerala", "admin2": "X", "country_code": "IN", "latitude": 9, "longitude": 76},
        {"name": "Salem", "admin1": "Tamil Nadu", "admin2": "Salem", "country_code": "IN", "latitude": 11.6, "longitude": 78.1}]})
    r = weather.geocode("Salem", "Tamil Nadu")
    assert len(r) == 2 and r[0]["state"] == "Tamil Nadu"


def test_forecast_uses_documented_params_and_caches(monkeypatch):
    calls = []
    def fake(url, params):
        calls.append((url, params))
        return {"current": {"temperature_2m": 30}, "daily": {"time": ["d"]}}
    monkeypatch.setattr(weather, "_get", fake); weather._cache.clear()
    weather.forecast(11.65, 78.16); weather.forecast(11.65, 78.16)
    assert len(calls) == 1 and calls[0][0] == weather.FORECAST_URL
    assert "relative_humidity_2m" in calls[0][1]["current"] and "precipitation_probability_max" in calls[0][1]["daily"]


def test_weather_failure_raises_instead_of_inventing_data(monkeypatch):
    def boom(*a, **k): raise requests.ConnectionError()
    monkeypatch.setattr(weather.requests, "get", boom)
    with pytest.raises(weather.WeatherError):
        weather._get(weather.FORECAST_URL, {})


def test_precautions_follow_the_numbers():
    hot = {"current": {"temperature_2m": 41, "relative_humidity_2m": 40, "wind_speed_10m": 5},
           "daily": {"temperature_2m_max": [41] * 3, "temperature_2m_min": [28] * 3, "precipitation_sum": [0] * 3,
                     "precipitation_probability_max": [5] * 3, "wind_speed_10m_max": [10] * 3}}
    assert "wp.heat" in weather.precaution_keys(hot) and "wp.dry" in weather.precaution_keys(hot)


# ------------------------------------------------------------------ speech services (Gnani mocked)
def _wav(frames=10, rate=24000):
    b = io.BytesIO()
    with wave.open(b, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(rate); w.writeframes(struct.pack("<h", 0) * frames)
    return b.getvalue()


def test_tts_chunks_long_answers_and_joins_audio(monkeypatch):
    sent = []
    def fake(text, **kw): sent.append((text, kw)); return _wav(10), "audio/wav"
    monkeypatch.setattr(G, "synthesize_speech", fake)
    long_text = "நெற்பயிருக்கு நீர் பாய்ச்சுங்கள். " * 80
    wav, all_spoken = tts_service.speak(long_text, L.get_language("tamil"))
    assert len(sent) > 1 and all(len(t) <= tts_service.CHUNK_CHARS for t, _ in sent)
    assert sent[0][1]["language"] == "ta-IN" and sent[0][1]["container"] == "wav"
    assert wave.open(io.BytesIO(wav)).getnframes() == 10 * len(sent)


def test_tts_refuses_languages_without_gnani_voice():
    with pytest.raises(G.GnaniError):
        tts_service.speak("hello", L.get_language("odia"))


def test_stt_default_uses_selected_language_and_original_request(monkeypatch):
    seen = {}
    def fake(data, name, mime, language_code, apply_itn, model=None):
        seen.update(code=language_code, model=model); return {"transcript": "నమస్కారం"}
    monkeypatch.setattr(G, "transcribe_audio", fake)
    text, det, err = stt_service.transcribe(b"x", "a.wav", "audio/wav", L.get_language("telugu"))
    assert (text, err) == ("నమస్కారం", None) and seen == {"code": "te-IN", "model": None}


def test_stt_auto_detect_falls_back_to_selected_language(monkeypatch):
    calls = []
    def fake(data, name, mime, language_code, apply_itn, model=None):
        calls.append((language_code, model))
        if model: raise G.GnaniError("Request failed", "Please try again.")
        return {"transcript": "வணக்கம்"}
    monkeypatch.setattr(G, "transcribe_audio", fake)
    text, _, err = stt_service.transcribe(b"x", "a.wav", "audio/wav", L.get_language("tamil"), auto_detect=True)
    assert text == "வணக்கம்" and calls == [("indic-auto", "prisma-v3.0"), ("ta-IN", None)]


def test_stt_empty_result_is_a_friendly_error(monkeypatch):
    monkeypatch.setattr(G, "transcribe_audio", lambda *a, **k: {"transcript": ""})
    _, _, err = stt_service.transcribe(b"x", "a.wav", "audio/wav", L.get_language("hindi"))
    assert err[0] == "No speech recognized"


# ------------------------------------------------------------------ schemes
def test_unverified_schemes_carry_no_verification_date_and_have_official_links():
    items = schemes.load()
    assert items and all(s["official_url"].startswith("https://") for s in items)
    assert any(s["last_verified"] for s in items) and any(not s["last_verified"] for s in items)
    assert all(s["verified_note"] for s in items if s["last_verified"])


# ------------------------------------------------------------------ photo upload safety and output escaping
def test_photo_pipeline_validates_resizes_and_strips_metadata():
    from PIL import Image
    import page_health as H
    b = io.BytesIO(); Image.new("RGB", (3000, 2000), (30, 120, 40)).save(b, "PNG")
    data, mime = H.prepare_image(b.getvalue())
    assert mime == "image/jpeg" and max(Image.open(io.BytesIO(data)).size) <= H.MAX_EDGE
    assert H.prepare_image(b"GIF89a....")[1] == "h.img_type"                       # wrong type
    assert H.prepare_image(b"\x89PNG\r\n\x1a\nnot really a png")[1] == "h.img_type"  # right header, undecodable
    assert H.prepare_image(b"\xff\xd8\xff" + b"0" * (5 * 1024 * 1024))[1] == "h.img_big"


def test_ai_text_is_html_escaped_before_display():
    import ui
    out = ui.rtl_wrap('<img src=x onerror=alert(1)><script>alert(2)</script>', "english")
    assert "<img" not in out and "<script" not in out and "&lt;script&gt;" in out
