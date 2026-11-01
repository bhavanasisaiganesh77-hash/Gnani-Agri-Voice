"""Text to Speech (Gnani Timbre voices through gnani_client.synthesize_speech)."""

from datetime import datetime

import streamlit as st

import database as db
import ui
import voices
from i18n import t
from gnani_client import GnaniError, synthesize_speech
from ui import card_head, notice

MAX_TTS_CHARS = 1000  # this app's own limit
QUALITY = {"Standard": 24000, "High": 48000}
FORMATS = {"WAV": "wav", "MP3": "mp3"}


def tts_page():
    user = ui.require_login()
    ui.page_header(t("nav.tts"), "volume")
    ready = ui.speech_ready()
    if not ready:
        ui.unavailable()

    with st.container(key="card_tts_options"):
        lang, usable = ui.language_picker("tts", "tts")
        model = voices.DEFAULT_MODEL
        names = [v for v, _ in voices.voices_for(model, lang.id)]  # voices built for this language come first
        c1, c2 = st.columns(2, gap="medium")
        with c1:
            voice = st.selectbox(t("t.voice"), names, key=f"tts_voice_{lang.id}")
        with c2:
            speed = st.slider(t("t.speed"), 0.85, 1.15, 1.0, 0.05, key="tts_speed")
        c3, c4 = st.columns(2, gap="medium")
        with c3:
            fmt_label = st.selectbox(t("t.format"), list(FORMATS), key="tts_format")
        with c4:
            quality_label = st.selectbox(t("t.quality"), list(QUALITY), format_func=lambda k: t("t.q_std") if k == "Standard" else t("t.q_high"), key="tts_quality")

    with st.container(key="card_tts_text"):
        text = st.text_area("Text", key="tts_text", height=190, max_chars=MAX_TTS_CHARS, label_visibility="collapsed",
                            placeholder=t("t.ph_text", lang=lang.native))
        st.markdown(f'<p class="hint count">{len(text)} / {MAX_TTS_CHARS}</p>', unsafe_allow_html=True)
        generate = st.button(t("t.generate"), key="gp_tts_generate", disabled=not (usable and ready and text.strip()))

    slot = st.empty()
    if generate:
        container, sample_rate = FORMATS[fmt_label], QUALITY[quality_label]
        fingerprint = (text.strip(), lang.id, voice, speed, container, sample_rate)
        if ui.debounce("tts", fingerprint):  # a repeated click on the same request does not call the API again
            st.session_state.pop("tts_error", None)
            ui.show_loading(slot, t("t.generating"))
            try:
                audio, mime = synthesize_speech(text.strip(), voice=voice, model=model, language=lang.tts_code,
                                                speed=speed, container=container, sample_rate=sample_rate)
            except GnaniError as err:
                st.session_state["tts_error"] = (err.title, err.detail)
                st.session_state.pop("tts_result", None)
            else:  # store results first, then update the screen
                st.session_state["tts_result"] = {"audio": audio, "mime": mime, "container": container}
                if user["save_history"]:
                    db.add_tts(user["id"], text.strip(), lang.name, lang.tts_code, voice, model, container, speed, audio)
            slot.empty()

    if st.session_state.get("tts_error"):
        notice("error", *st.session_state["tts_error"])

    result = st.session_state.get("tts_result")
    if result:  # shown only when a valid audio file exists
        with st.container(key="card_tts_result"):
            card_head("volume", t("t.audio"))
            st.audio(result["audio"], format=result["mime"])
            st.download_button(t("t.dl_audio"), data=result["audio"],
                               file_name=f"speech-{datetime.now():%Y%m%d-%H%M%S}.{result['container']}",
                               mime=result["mime"], key="gp_tts_download")
