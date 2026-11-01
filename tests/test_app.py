"""Run the real Streamlit pages with AppTest: login, language restore/switch, every page in several languages,
and the full assistant flow with the external services (LLM, Gnani TTS, Open-Meteo) replaced by fakes."""
import io
import struct
import wave

import pytest
from streamlit.testing.v1 import AppTest

import agri_service
import gnani_client as G
import llm_service as S
import tts_service
import weather

ROOT = "/home/claude/Gnani-Voice-Studio"
LANGS = ["english", "telugu", "tamil", "hindi", "assamese"]  # assamese = no translation file, no voice


def _harness():
    import importlib

    import streamlit as st

    from styles import BASE_CSS
    st.markdown(BASE_CSS, unsafe_allow_html=True)
    mod, fn = st.session_state["_page"]
    getattr(importlib.import_module(mod), fn)()


def make_wav(frames=20):
    b = io.BytesIO()
    with wave.open(b, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(24000); w.writeframes(struct.pack("<h", 0) * frames)
    return b.getvalue()


class FakeLLM(S.LLMProvider):
    name, supports_images = "fake", True

    def __init__(self, reply="సమాధానం: నీరు పెట్టండి."):
        self.reply, self.calls = reply, []

    def is_configured(self): return True

    def generate(self, system, messages, max_tokens=900, temperature=0.3, image=None):
        self.calls.append({"system": system, "messages": messages, "image": image})
        return self.reply


@pytest.fixture
def fake_llm(monkeypatch):
    fake = FakeLLM()
    monkeypatch.setattr(S, "get_provider", lambda: fake)
    return fake


@pytest.fixture
def fake_speech(monkeypatch):
    calls = []
    monkeypatch.setattr(G, "synthesize_speech", lambda text, **kw: (calls.append((text, kw)) or make_wav(), "audio/wav"))
    monkeypatch.setattr("ui.speech_ready", lambda: True)
    return calls


FORECAST = {"current": {"temperature_2m": 31.2, "relative_humidity_2m": 88, "wind_speed_10m": 12, "precipitation": 0},
            "daily": {"time": ["2026-10-31", "2026-11-01", "2026-11-02", "2026-11-03"],
                      "temperature_2m_max": [33, 32, 31, 31], "temperature_2m_min": [24, 23, 23, 22],
                      "precipitation_sum": [0, 2, 60, 5], "precipitation_probability_max": [10, 40, 90, 30],
                      "wind_speed_10m_max": [14, 15, 20, 12]}}


@pytest.fixture
def fake_weather(monkeypatch):
    monkeypatch.setattr(weather, "forecast", lambda lat, lon: FORECAST)
    monkeypatch.setattr(weather, "geocode", lambda name, state="", limit=5: [
        {"name": name, "state": state or "Tamil Nadu", "latitude": 11.65, "longitude": 78.16, "label": f"{name}, Tamil Nadu"}])


def page(module, fn, user, lang="english", setup=None):
    at = AppTest.from_function(_harness, default_timeout=60)
    at.session_state["user"] = user
    at.session_state["lang_id"] = lang
    at.session_state["_page"] = (module, fn)
    if setup:
        setup(at)
    return at.run()


def no_errors(at):
    assert not at.exception, [e.value for e in at.exception]


# ------------------------------------------------------------------ entrypoint: login, language restore, language switch
def _entry():
    return AppTest.from_file(f"{ROOT}/streamlit_app.py", default_timeout=60)


def test_login_screen_language_selector_changes_whole_screen(fresh_db):
    at = _entry().run(); no_errors(at)
    assert "Log in" in " ".join(m.value for m in at.markdown)
    at.selectbox(key="lang_sel_login").select("tamil").run(); no_errors(at)
    assert "உள்நுழை" in " ".join(m.value for m in at.markdown)
    assert at.session_state["lang_id"] == "tamil"


def test_login_restores_saved_language_then_switching_persists(fresh_db, user):
    fresh_db.set_language(user["id"], "tamil")
    at = _entry().run()
    at.text_input[0].set_value("farmer@example.com"); at.text_input[1].set_value("Passw0rd1")
    at.button(key="FormSubmitter:login_form-Log in").click().run() if False else None
    submit = [b for b in at.button if b.key and "gp_login_submit" in b.key]
    submit[0].click().run(); no_errors(at)
    assert at.session_state["lang_id"] == "tamil"  # restored from the database at login
    assert "உங்கள் பண்ணை" in " ".join(m.value for m in at.markdown) or "வரவேற்கிறோம்" in " ".join(m.value for m in at.markdown)
    # switch language from the sidebar: saved for next time, history untouched
    cid = fresh_db.create_conversation(user["id"], "old chat", "Tamil", "ta-IN")
    fresh_db.add_message(user["id"], cid, "user", "பழைய கேள்வி", language="tamil")
    at.selectbox(key="lang_sel_sidebar").select("telugu").run(); no_errors(at)
    assert fresh_db.get_user(user["id"])["default_language"] == "telugu"
    assert fresh_db.get_messages(user["id"], cid)[0]["content"] == "பழைய கேள்வி"
    assert "స్వాగతం" in " ".join(m.value for m in at.markdown)


def test_wrong_password_shows_translated_error(fresh_db, user):
    at = _entry().run()
    at.selectbox(key="lang_sel_login").select("telugu").run()
    at.text_input[0].set_value("farmer@example.com"); at.text_input[1].set_value("nope")
    [b for b in at.button if b.key and "gp_login_submit" in b.key][0].click().run(); no_errors(at)
    assert "తప్పు" in " ".join(m.value for m in at.markdown)


# ------------------------------------------------------------------ every page renders in every language
PAGES = [("page_dashboard", "dashboard_page"), ("page_ask", "ask_page"), ("page_crops", "crops_page"),
         ("page_health", "health_page"), ("page_weather", "weather_page"), ("page_schemes", "schemes_page"),
         ("page_history", "history_page"), ("page_account", "profile_page"), ("page_account", "settings_page"),
         ("page_help", "help_page"), ("page_stt", "live_page"), ("page_stt", "upload_page"), ("page_tts", "tts_page")]


@pytest.mark.parametrize("lang", LANGS)
@pytest.mark.parametrize("module,fn", PAGES)
def test_every_page_renders_without_errors(fresh_db, user, fake_weather, module, fn, lang):
    fresh_db.save_profile(user["id"], "Tamil Nadu", "Salem", "paddy", 2, 11.65, 78.16, "Salem, Tamil Nadu")
    at = page(module, fn, fresh_db.get_user(user["id"]), lang)
    no_errors(at)


def test_untranslated_language_shows_clear_notice_but_voice_off(fresh_db, user):
    at = page("page_ask", "ask_page", user, "assamese"); no_errors(at)
    text = " ".join(m.value for m in at.markdown)
    assert "not yet translated into Assamese" in text and "Voice is not available" in text


# ------------------------------------------------------------------ assistant: typed question -> answer -> voice
def _ask(at, question):
    at.text_area(key="ask_draft").set_value(question)
    at.button(key="gp_ask_send").click()
    return at.run()


def test_typed_question_gets_answer_saved_and_spoken(fresh_db, user, fake_llm, fake_speech):
    fresh_db.save_profile(user["id"], "Andhra Pradesh", "Guntur", "paddy", None)
    at = page("page_ask", "ask_page", user, "telugu")
    at = _ask(at, "నా వరి పంట ఆకులు పసుపు రంగులోకి మారుతున్నాయి. ఏం చేయాలి?"); no_errors(at)
    call = fake_llm.calls[0]
    assert "Telugu" in call["system"] and "Guntur" in call["system"]           # language + farm context
    assert call["messages"][-1]["content"].startswith("నా వరి పంట")
    convs = fresh_db.list_conversations(user["id"])
    msgs = fresh_db.get_messages(user["id"], convs[0]["id"])
    assert [m["role"] for m in msgs] == ["user", "assistant"] and msgs[0]["language"] == "telugu"
    assert fake_speech and fake_speech[0][1]["language"] == "te-IN"            # Timbre called in the farmer's language
    assert at.get("audio"), "an audio player with controls should be shown"


def test_conversation_context_is_remembered(fresh_db, user, fake_llm, fake_speech):
    at = page("page_ask", "ask_page", user, "telugu")
    at = _ask(at, "మొదటి ప్రశ్న")
    at = _ask(at, "రెండో ప్రశ్న"); no_errors(at)
    sent = [m["content"] for m in fake_llm.calls[1]["messages"]]
    assert sent[0] == "మొదటి ప్రశ్న" and sent[-1] == "రెండో ప్రశ్న" and len(sent) == 3


def test_regenerate_replaces_the_last_answer(fresh_db, user, fake_llm, fake_speech):
    at = _ask(page("page_ask", "ask_page", user, "tamil"), "என் நெற்பயிரின் இலைகள் மஞ்சள் நிறமாக மாறுகின்றன. என்ன செய்ய வேண்டும்?")
    fake_llm.reply = "இரண்டாவது பதில்"
    at.button(key="gs_regen").click().run(); no_errors(at)
    msgs = fresh_db.get_messages(user["id"], fresh_db.list_conversations(user["id"])[0]["id"])
    assert [m["content"] for m in msgs][-1] == "இரண்டாவது பதில்" and len(msgs) == 2


def test_feedback_is_stored(fresh_db, user, fake_llm, fake_speech):
    at = _ask(page("page_ask", "ask_page", user, "hindi"), "मेरी धान की फसल की पत्तियाँ पीली हो रही हैं। मुझे क्या करना चाहिए?")
    up = [b for b in at.button if b.key and b.key.startswith("gs_up_")][0]
    up.click().run(); no_errors(at)
    msgs = fresh_db.get_messages(user["id"], fresh_db.list_conversations(user["id"])[0]["id"])
    assert msgs[-1]["feedback"] == 1


def test_no_voice_for_unsupported_language_but_text_answer_works(fresh_db, user, fake_llm, fake_speech):
    at = _ask(page("page_ask", "ask_page", user, "odia"), "ମୋ ଧାନ ପତ୍ର ହଳଦିଆ ହେଉଛି"); no_errors(at)
    assert fake_llm.calls and "Odia" in fake_llm.calls[0]["system"]
    assert fake_speech == [] and not at.get("audio")


def test_assistant_unavailable_is_handled_politely(fresh_db, user, monkeypatch):
    class Off(FakeLLM):
        def is_configured(self): return False
    monkeypatch.setattr(S, "get_provider", lambda: Off())
    at = _ask(page("page_ask", "ask_page", user, "english"), "When to irrigate cotton?"); no_errors(at)
    assert "not available right now" in " ".join(m.value for m in at.markdown)


def test_rate_limit_message(fresh_db, user, fake_llm, monkeypatch):
    monkeypatch.setenv("AI_REPLIES_PER_HOUR", "1")
    at = _ask(page("page_ask", "ask_page", user, "english"), "q1")
    at = _ask(at, "q2"); no_errors(at)
    assert "many questions" in " ".join(m.value for m in at.markdown)


def test_history_saving_off_keeps_chat_out_of_database(fresh_db, user, fake_llm, fake_speech):
    fresh_db.update_preferences(user["id"], "english", False, False)
    at = _ask(page("page_ask", "ask_page", fresh_db.get_user(user["id"]), "english"), "Fertilizer for maize?"); no_errors(at)
    assert fresh_db.list_conversations(user["id"]) == [] and fake_llm.calls


def test_regional_user_cannot_open_someone_elses_conversation(fresh_db, user, fake_llm):
    other, _ = fresh_db.create_user("o@example.com", "Other", "Passw0rd1")
    cid = fresh_db.create_conversation(other["id"], "secret", "English", "en-IN")
    fresh_db.add_message(other["id"], cid, "user", "my secret question")
    at = page("page_ask", "ask_page", user, "english", setup=lambda a: a.session_state.__setitem__("open_conv", cid))
    no_errors(at)
    assert "my secret question" not in " ".join(m.value for m in at.markdown)


# ------------------------------------------------------------------ crop advice, plant health, schemes, weather, profile
def test_crop_advice_sends_form_details_and_saves_history(fresh_db, user, fake_llm, fake_speech):
    # English UI here: AppTest evaluates radio format_func outside the page's language context (a harness quirk).
    # The Telugu rendering of this page is covered by test_every_page_renders_without_errors.
    at = page("page_crops", "crops_page", user, "english")
    at.selectbox(key="crops_crop").select("cotton")
    at.selectbox(key="crops_state").select("Telangana")
    at.text_input(key="crops_district").set_value("Warangal")
    at.text_area(key="crops_symptoms").set_value("leaves curling")
    at.button(key="gp_crops_go").click().run(); no_errors(at)
    req = fake_llm.calls[0]["messages"][0]["content"]
    for must in ("Cotton", "Telangana", "Warangal", "leaves curling"):
        assert must in req
    assert "English" in fake_llm.calls[0]["system"]
    assert fresh_db.list_conversations(user["id"])[0]["title"].startswith("General advice")


def test_crop_advice_other_crop_requires_a_name(fresh_db, user, fake_llm):
    at = page("page_crops", "crops_page", user, "english")
    at.selectbox(key="crops_crop").select("other")
    at.run()
    at.button(key="gp_crops_go").click().run(); no_errors(at)
    assert not fake_llm.calls and "crop name" in " ".join(m.value for m in at.markdown)


def test_dashboard_topic_shortcut_preselects_topic(fresh_db, user):
    at = page("page_crops", "crops_page", user, "english", setup=lambda a: a.session_state.__setitem__("crop_topic", "irrigation"))
    assert at.radio(key="crops_topic").value == "irrigation"


def test_plant_health_shows_possible_causes_never_confirmed(fresh_db, user, monkeypatch):
    import i18n  # AppTest reads widget labels outside the page run; pin the language so both sides agree
    monkeypatch.setattr(i18n, "current_lang_id", lambda: "telugu")
    fake = FakeLLM('{"summary":"పసుపు ఆకులు","possible_causes":["నత్రజని లోపం","నీటి ఎద్దడి"],"signs_to_check":["పాత ఆకులు"],'
                   '"next_steps":["పొలాన్ని పరిశీలించండి"],"prevention":["సమతుల ఎరువులు"],"when_to_call_expert":"KVK","confidence":"high"}')
    monkeypatch.setattr(S, "get_provider", lambda: fake)
    at = page("page_health", "health_page", user, "telugu")
    at.text_area(key="health_desc").set_value("ఆకులు పసుపు రంగులోకి మారుతున్నాయి")
    at.button(key="gp_health_go").click().run(); no_errors(at)
    shown = " ".join(m.value for m in at.markdown)
    assert "సాధ్యమయ్యే కారణాలు" in shown and "నత్రజని లోపం" in shown
    assert "నిర్ధారిత నిర్ధారణ కాదు" in shown                                  # not-a-diagnosis banner (Telugu)
    assert "DISEASE" not in shown and "disease_request" not in shown
    assert "Never say the problem is confirmed" in fake.calls[0]["messages"][0]["content"]


def test_plant_health_requires_some_input(fresh_db, user, fake_llm):
    at = page("page_health", "health_page", user, "english")
    at.button(key="gp_health_go").click().run(); no_errors(at)
    assert not fake_llm.calls and "describe the problem" in " ".join(m.value for m in at.markdown)


def test_plant_health_handles_non_json_reply(fresh_db, user, monkeypatch):
    monkeypatch.setattr(S, "get_provider", lambda: FakeLLM("Sorry, plain text answer"))
    at = page("page_health", "health_page", user, "english")
    at.text_area(key="health_desc").set_value("brown spots")
    at.button(key="gp_health_go").click().run(); no_errors(at)
    assert "plain text answer" in " ".join(m.value for m in at.markdown)


def test_scheme_page_shows_verification_status(fresh_db, user):
    at = page("page_schemes", "schemes_page", user, "english"); no_errors(at)
    assert "Last checked: 2026-10-30" in " ".join(c.value for c in at.caption)   # PM-KISAN is first
    at.selectbox(key="scheme_pick").select("kcc").run(); no_errors(at)
    assert "not been checked yet" in " ".join(m.value for m in at.markdown)


def test_scheme_explanation_is_grounded_in_listed_facts(fresh_db, user, fake_llm):
    at = page("page_schemes", "schemes_page", user, "tamil")
    at.button(key="gp_scheme_explain").click().run(); no_errors(at)
    req = fake_llm.calls[0]["messages"][0]["content"]
    assert "ONLY the facts" in req and "pmkisan.gov.in" in req and "Tamil" in fake_llm.calls[0]["system"]


def test_weather_page_uses_saved_location_and_real_data(fresh_db, user, fake_weather):
    fresh_db.save_profile(user["id"], "Tamil Nadu", "Salem", "paddy", None, 11.65, 78.16, "Salem, Tamil Nadu")
    at = page("page_weather", "weather_page", user, "english"); no_errors(at)
    metrics = {m.label: m.value for m in at.metric}
    assert metrics["Temperature"] == "31 °C" and metrics["Humidity"] == "88 %"
    assert "Heavy rain expected" in " ".join(m.value for m in at.markdown)      # from the 60 mm forecast day


def test_weather_service_down_shows_message_not_fake_numbers(fresh_db, user, monkeypatch):
    fresh_db.save_profile(user["id"], "Tamil Nadu", "Salem", "paddy", None, 11.65, 78.16, "Salem")
    def down(*a, **k): raise weather.WeatherError("x")
    monkeypatch.setattr(weather, "forecast", down)
    at = page("page_weather", "weather_page", user, "english"); no_errors(at)
    assert not at.metric and "could not be loaded" in " ".join(m.value for m in at.markdown)


def test_profile_save_geocodes_district_for_weather(fresh_db, user, fake_weather):
    at = page("page_account", "profile_page", user, "english")
    at.selectbox[1].select("Tamil Nadu")
    at.text_input[0].set_value("Salem")
    at.selectbox[2].select("paddy")
    [b for b in at.button if b.key and "gp_farm_save" in b.key][0].click().run(); no_errors(at)
    p = fresh_db.get_profile(user["id"])
    assert (p["state"], p["district"], p["primary_crop"]) == ("Tamil Nadu", "Salem", "paddy") and p["latitude"] == 11.65
