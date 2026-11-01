"""Ask AgriVoice: speak, upload or type a farming question; check the transcript; get an answer in the farmer's
language as text and (where Gnani supports the language) as speech.

Flow: voice -> Gnani Prisma STT -> editable transcript -> LLM -> answer -> Gnani Timbre TTS -> audio with replay.
"""

import hashlib
import logging

import streamlit as st

import agri_prompts
import agri_service
import audio_utils
import database as db
import gnani_client as G
import languages as L
import stt_service
import tts_service
import ui
from chat_store import get_store
from i18n import t

log = logging.getLogger("agrivoice.ask")
MAX_QUESTION_CHARS = 1000
AUDIO_CACHE = "ask_audio"  # message id -> wav bytes (this session only; audio is never written to disk)


# ----------------------------------------------------------------------------- callbacks (run before the page redraws)
def _submit():
    text = " ".join((st.session_state.get("ask_draft") or "").split())
    if text:
        st.session_state["ask_pending"] = {"text": text[:MAX_QUESTION_CHARS], "mode": st.session_state.get("ask_mode_used", "text"),
                                           "raw": st.session_state.get("ask_raw")}
        st.session_state["ask_draft"] = ""
        st.session_state["ask_raw"] = None
        st.session_state["ask_mode_used"] = "text"


def _regen():
    st.session_state["ask_regen"] = True


def _new_chat():
    for k in ("ask_conv_id", "ask_mem", "ask_pending", "ask_regen", "ask_draft", "ask_raw", AUDIO_CACHE, "ask_autoplay"):
        st.session_state.pop(k, None)


def _delete_chat(store):
    store.delete()
    _new_chat()


def _rate(store, message_id, value):
    if store.feedback(message_id, value):
        st.toast(t("a.thanks"))


# ----------------------------------------------------------------------------- helpers
def _listen(store, lang, message, autoplay=False, user=None):
    """Create (or reuse) the spoken version of an assistant message and show a player with controls."""
    cache = st.session_state.setdefault(AUDIO_CACHE, {})
    mid = message["id"]
    if mid not in cache:
        slot = st.empty()
        ui.show_loading(slot, t("a.speaking"))
        try:
            wav, _all = tts_service.speak(message["content"], lang)
            cache[mid] = wav
        except G.GnaniError as err:
            log.info("tts failed: %s", err.title)
            slot.empty()
            ui.notice("warn", t("a.voice_fail"))
            return
        slot.empty()
    st.audio(cache[mid], format="audio/wav", autoplay=autoplay)


def _answer_flow(user, store, lang, profile):
    """Ask the LLM with the conversation so far, save the reply, and (optionally) speak it."""
    slot = st.empty()
    ui.show_loading(slot, t("a.thinking"))
    history = [{"role": m["role"], "content": m["content"]} for m in store.messages()]
    try:
        reply = agri_service.answer(user["id"], history, lang, profile)
    except agri_service.AnswerError as err:
        slot.empty()
        ui.notice("warn", t("a.limit") if err.kind == "rate_limit" else t("a.llm_down"))
        return
    slot.empty()
    mid = store.add("assistant", reply, lang)
    if mid is not None and user["voice_reply"] and L.is_usable(lang, "tts") and ui.speech_ready():
        st.session_state["ask_autoplay"] = mid
    st.rerun()


def _stt(user, lang, data, filename):
    """Validate, transcribe and put the text into the editable box. Returns True when the page should redraw."""
    error, _dur, mime = audio_utils.validate_audio(filename, data)
    if error:
        ui.notice("error", *error)
        return False
    slot = st.empty()
    ui.show_loading(slot, t("a.transcribing"))
    text, detected_lang, err = stt_service.transcribe(
    data,
    filename,
    mime,
    lang,
    auto_detect=st.session_state.get("ask_detect", False),
    itn=user["apply_itn"]
)
    slot.empty()
    if err:
        ui.notice("error", *err)
        return False
    st.session_state["ask_draft"] = text
    st.session_state["ask_raw"] = text
    st.session_state["ask_mode_used"] = "voice"
    return True


# ----------------------------------------------------------------------------- page
def ask_page():
    user = ui.require_login()
    lang = ui.current_language()
    store = get_store(user, st.session_state)
    profile = db.get_profile(user["id"])
    ui.page_header(t("a.title"), "mic")
    st.markdown(f'<p class="hint">{ui.esc(t("a.intro"))}</p>', unsafe_allow_html=True)

    # resume a conversation chosen on the Home or History page
    if (cid := st.session_state.pop("open_conv", None)) and store.persistent:
        if db.get_messages(user["id"], cid):
            st.session_state["ask_conv_id"] = cid

    voice_ok = L.is_usable(lang, "stt") and ui.speech_ready()
    speak_ok = L.is_usable(lang, "tts") and ui.speech_ready()

    with st.container(key="card_ask_top"):
        c1, c2 = st.columns([3, 2])
        with c1:
            ui.language_selector("ask")
        with c2:
            if speak_ok:
                new_val = st.toggle(t("a.autoplay"), value=user["voice_reply"], key="ask_voice_toggle")
                if new_val != user["voice_reply"]:
                    db.set_voice_reply(user["id"], new_val)
                    user["voice_reply"] = new_val
            st.toggle(t("a.detect"), value=False, key="ask_detect", disabled=not ui.speech_ready(), help=t("a.detect_note"))
        if not voice_ok:
            ui.notice("info", "", t("a.voice_na", lang=lang.native))
        if (ctx := agri_prompts.profile_context(profile)):
            st.markdown(f'<p class="hint">{ui.esc(t("a.ctx", ctx=ctx))}</p>', unsafe_allow_html=True)

    # ---- conversation
    msgs = store.messages()
    last_assistant = next((m for m in reversed(msgs) if m["role"] == "assistant"), None)
    if not msgs:
        st.markdown(f'<p class="hint"><b>{ui.esc(t("a.empty"))}</b></p>', unsafe_allow_html=True)
        for i, key in enumerate(("a.ex1", "a.ex2", "a.ex3")):
            if st.button(t(key), key=f"gs_ask_ex{i}", use_container_width=True):
                st.session_state["ask_draft"] = t(key)
                st.rerun()
    for m in msgs:
        role = m["role"]
        with st.chat_message("user" if role == "user" else "assistant"):
            who = t("a.you") if role == "user" else t("a.ai")
            st.markdown(f"**{ui.esc(who)}**", unsafe_allow_html=True)
            st.markdown(ui.rtl_wrap(m["content"], m.get("language") or lang.id), unsafe_allow_html=True)
            if role == "assistant":
                is_last = last_assistant is not None and m["id"] == last_assistant["id"]
                autoplay = st.session_state.get("ask_autoplay") == m["id"]
                cached = m["id"] in st.session_state.get(AUDIO_CACHE, {})
                if cached or autoplay:
                    _listen(store, lang, m, autoplay=autoplay, user=user)
                    if autoplay:
                        st.session_state.pop("ask_autoplay", None)
                elif speak_ok:
                    if st.button(t("a.listen"), key=f"gs_listen_{m['id']}"):
                        _listen(store, lang, m, user=user)
                if is_last:
                    b1, b2, b3, b4 = st.columns(4)
                    with b1:
                        ui.copy_button(m["content"], False, "__none__", label=t("a.copy"), copied=t("t.copied"))
                    with b2:
                        st.button(t("a.regen"), key="gs_regen", on_click=_regen)
                    with b3:
                        st.button("👍 " + t("a.good"), key=f"gs_up_{m['id']}", on_click=_rate, args=(store, m["id"], 1))
                    with b4:
                        st.button("👎 " + t("a.bad"), key=f"gs_down_{m['id']}", on_click=_rate, args=(store, m["id"], -1))
    if msgs:
        st.caption(t("c.disclaimer"))

    # ---- pending work (set by callbacks)
    pending, regen = st.session_state.pop("ask_pending", None), st.session_state.pop("ask_regen", None)
    if pending:
        mid = store.add("user", pending["text"], lang, input_mode=pending["mode"], raw=pending["raw"], title=pending["text"][:60])
        if mid is None:
            ui.unavailable()
        else:
            _answer_flow(user, store, lang, profile)
    elif regen and last_assistant is not None:
        store.drop_last_assistant()
        st.session_state.get(AUDIO_CACHE, {}).pop(last_assistant["id"], None)
        _answer_flow(user, store, lang, profile)

    # ---- input
    with st.container(key="card_ask_input"):
        mode = st.segmented_control(" ", ["speak", "upload", "type"], default="speak" if voice_ok else "type",
                                    format_func=lambda x: {"speak": "🎤 " + t("a.tab_live"), "upload": "📁 " + t("a.tab_up"),
                                                           "type": "⌨️ " + t("a.tab_type")}[x],
                                    key="ask_mode", label_visibility="collapsed") or "type"
        gen = st.session_state.setdefault("ask_gen", 0)
        if mode == "speak" and voice_ok:
            audio = st.audio_input(t("a.record"), key=f"ask_mic_{gen}")
            if audio is not None:
                data = audio.getvalue()
                digest = hashlib.sha256(data).hexdigest()
                if digest != st.session_state.get("ask_last_hash") and ui.debounce("ask_mic", digest):
                    st.session_state["ask_last_hash"] = digest
                    if _stt(user, lang, data, "ask.wav"):
                        st.session_state["ask_gen"] = gen + 1
                        st.rerun()
        elif mode == "upload" and voice_ok:
            up = st.file_uploader(t("a.tab_up"), type=audio_utils.ALLOWED_EXTENSIONS, key=f"ask_up_{gen}", label_visibility="collapsed")
            if up is not None:
                data = up.getvalue()
                digest = hashlib.sha256(data).hexdigest()
                if digest != st.session_state.get("ask_last_hash"):
                    st.session_state["ask_last_hash"] = digest
                    if _stt(user, lang, data, up.name):
                        st.session_state["ask_gen"] = gen + 1
                        st.rerun()
        elif mode in ("speak", "upload"):
            ui.notice("info", "", t("a.voice_na", lang=lang.native))

        from_voice = st.session_state.get("ask_mode_used") == "voice"
        st.text_area(t("a.tr_label") if from_voice else t("a.ph"), key="ask_draft", height=110, max_chars=MAX_QUESTION_CHARS,
                     placeholder=t("a.ph"), label_visibility="visible")
        if from_voice:
            st.markdown(f'<p class="hint">{ui.esc(t("a.tr_hint"))}</p>', unsafe_allow_html=True)
        c1, c2, c3 = st.columns([3, 1.3, 1])
        with c1:
            st.button(t("a.send"), key="gp_ask_send", on_click=_submit, use_container_width=True)
        with c2:
            st.button(t("a.new"), key="gs_ask_new", on_click=_new_chat, use_container_width=True)
        with c3:
            if msgs:
                st.button(t("c.delete"), key="gs_ask_delete", on_click=_delete_chat, args=(store,), use_container_width=True)
