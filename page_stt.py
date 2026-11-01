"""Speech to Text: 'Speak Live' (record a clip, transcribed as soon as you stop) and
'Record / Upload' (record or upload a file, then transcribe).

The Gnani request itself is unchanged and lives in gnani_client.transcribe_audio.
"""

import hashlib
from datetime import datetime

import streamlit as st

import database as db
import ui
from i18n import t
from audio_utils import ALLOWED_EXTENSIONS, fmt_duration, validate_audio
from gnani_client import GnaniError, extract_transcript, transcribe_audio
from ui import card_head, notice, pill


def transcribe_clip(data, filename, mime, lang, itn):
    """One call to the existing Gnani client. Returns (text, error tuple or None)."""
    try:
        result = transcribe_audio(data, filename, mime, language_code=lang.stt_code, apply_itn=itn)
    except GnaniError as err:
        return "", (err.title, err.detail)
    text = extract_transcript(result)
    if not text:
        return "", ("No speech recognized", "Check that the audio is clear and spoken in the selected language.")
    return text, None


def transcript_download(text, key):
    st.download_button(t("c.download"), data=text.encode("utf-8"),
                       file_name=f"transcript-{datetime.now():%Y%m%d-%H%M%S}.txt", mime="text/plain",
                       disabled=not text.strip(), key=key)


def _edit_hint(text):
    if text.strip():
        st.markdown(f'<p class="hint">{ui.esc(t("t.edit_hint"))}</p>', unsafe_allow_html=True)


# ------------------------------------------------------------------------------ Speak Live
def _reset_live():
    for k, v in {"live_text": "", "live_error": None, "live_last_hash": None}.items():
        st.session_state[k] = v
    st.session_state["live_gen"] = st.session_state.get("live_gen", 0) + 1


def live_page():
    user = ui.require_login()
    ui.page_header(t("nav.live"), "mic")
    for k, v in {"live_text": "", "live_error": None, "live_last_hash": None, "live_gen": 0}.items():
        st.session_state.setdefault(k, v)
    ready = ui.speech_ready()
    if not ready:
        ui.unavailable()

    with st.container(key="card_live_input"):
        lang, usable = ui.language_picker("live", "stt")
        itn = st.toggle(t("t.fmt_numbers"), value=user["apply_itn"], key="live_itn")
        audio = st.audio_input("Record", key=f"live_mic_{st.session_state.live_gen}", label_visibility="collapsed")

    slot = st.empty()
    if audio is not None and usable and ready:
        data = audio.getvalue()
        digest = hashlib.sha256(data).hexdigest()
        if digest != st.session_state.live_last_hash and ui.debounce("live", (digest, lang.id, itn)):
            st.session_state.live_last_hash = digest
            st.session_state.live_error = None
            error, _dur, mime = validate_audio("live.wav", data)
            if error:
                st.session_state.live_error = error
            else:
                ui.show_loading(slot, t("t.transcribing"))
                text, error = transcribe_clip(data, "live.wav", mime, lang, itn)
                if error:
                    st.session_state.live_error = error
                else:  # store the result before touching the screen again
                    current = st.session_state.live_text.strip()
                    st.session_state.live_text = f"{current}\n{text}" if current else text
                    st.session_state.live_gen += 1  # fresh microphone, ready for the next clip
                slot.empty()
                if not error:
                    st.rerun()

    if st.session_state.live_error:
        notice("error", *st.session_state.live_error)

    with st.container(key="card_live_text"):
        card_head("mic", t("t.transcript"))
        st.text_area(t("t.transcript"), key="live_text", height=260, label_visibility="collapsed", placeholder=t("t.ph_tr"))
        text = st.session_state.live_text
        _edit_hint(text)
        c1, c2, c3, c4 = st.columns(4, gap="small")
        with c1:
            ui.copy_button(text, not text.strip(), t("t.transcript"), t("t.copy_tr"), t("t.copied"))
        with c2:
            transcript_download(text, "gg_live_dl")
        with c3:
            if st.button(t("c.save"), key="gg_live_save", disabled=not text.strip()):
                db.add_history(user["id"], "Speak Live", lang.name, lang.stt_code or "", None, text)
                st.toast(t("c.saved"))
        with c4:
            st.button(t("c.clear"), key="gg_live_new", on_click=_reset_live, disabled=not text.strip())


# ------------------------------------------------------------------------------ Record / Upload
def upload_page():
    user = ui.require_login()
    ui.page_header(t("nav.upload"), "upload")
    for k, v in {"ru_text": "", "ru_source": None, "ru_error": None}.items():
        st.session_state.setdefault(k, v)
    ready = ui.speech_ready()
    if not ready:
        ui.unavailable()

    with st.container(key="card_ru_options"):
        lang, usable = ui.language_picker("ru", "stt")
        itn = st.toggle(t("t.fmt_numbers"), value=user["apply_itn"], key="ru_itn")

    rec_clicked = upl_clicked = False
    recording = uploaded = None
    rec_err = upl_err = None
    rec_bytes = up_bytes = b""
    rec_mime = up_mime = ""
    with st.container(key="band"):
        left, right = st.columns(2, gap="large")
        with left:
            with st.container(key="card_ru_record"):
                card_head("mic", t("t.record"))
                recording = st.audio_input("Record", label_visibility="collapsed", key="ru_mic")
                if recording is not None:
                    rec_bytes = recording.getvalue()
                    rec_err, rec_dur, rec_mime = validate_audio("recording.wav", rec_bytes)
                    if rec_err:
                        notice("error", *rec_err)
                    elif rec_dur:
                        pill(fmt_duration(rec_dur), "ready")
                rec_clicked = st.button(t("t.transcribe"), key="gp_ru_rec",
                                        disabled=recording is None or bool(rec_err) or not usable or not ready)
        with right:
            with st.container(key="card_ru_upload"):
                card_head("upload", t("t.upload"))
                uploaded = st.file_uploader("Upload", type=ALLOWED_EXTENSIONS, label_visibility="collapsed", key="ru_upload")
                if uploaded is not None:
                    up_bytes = uploaded.getvalue()
                    upl_err, up_dur, up_mime = validate_audio(uploaded.name, up_bytes)
                    if upl_err:
                        notice("error", *upl_err)
                    else:
                        st.audio(up_bytes, format=up_mime)
                        if up_dur:
                            pill(fmt_duration(up_dur), "ready")
                upl_clicked = st.button(t("t.transcribe"), key="gp_ru_upl",
                                        disabled=uploaded is None or bool(upl_err) or not usable or not ready)

    slot = st.empty()
    job = None
    if rec_clicked and recording is not None:
        job = ("recording", rec_bytes, "recording.wav", rec_mime)
    elif upl_clicked and uploaded is not None:
        job = ("uploaded file", up_bytes, uploaded.name, up_mime)
    if job:
        source, data, filename, mime = job
        fingerprint = (hashlib.sha256(data).hexdigest(), lang.id, itn)
        if ui.debounce("ru", fingerprint):  # a repeated click on the same audio does not call the API again
            st.session_state.ru_error = None
            ui.show_loading(slot, t("t.transcribing"))
            text, error = transcribe_clip(data, filename, mime, lang, itn)
            if error:  # store results first, then update the screen
                st.session_state.ru_error = error
            else:
                st.session_state.ru_text = text
                st.session_state.ru_source = source
                if user["save_history"]:
                    db.add_history(user["id"], "Record / Upload", lang.name, lang.stt_code or "", filename, text)
            slot.empty()

    if st.session_state.ru_error:
        notice("error", *st.session_state.ru_error)

    with st.container(key="card_ru_text"):
        card_head("upload", t("t.transcript"))
        st.text_area(t("t.transcript"), key="ru_text", height=300, label_visibility="collapsed", placeholder=t("t.ph_tr"))
        text = st.session_state.ru_text
        _edit_hint(text)
        c1, c2, c3 = st.columns(3, gap="small")
        with c1:
            ui.copy_button(text, not text.strip(), t("t.transcript"), t("t.copy_tr"), t("t.copied"))
        with c2:
            transcript_download(text, "gg_ru_dl")
        with c3:
            st.button(t("c.clear"), key="gg_ru_clear", disabled=not text.strip(),
                      on_click=lambda: st.session_state.update(ru_text="", ru_source=None, ru_error=None))
