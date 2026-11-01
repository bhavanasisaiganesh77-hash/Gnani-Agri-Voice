"""History: conversations, transcripts and generated speech. Every query is scoped to the signed-in user."""

import streamlit as st

import database as db
import ui
from i18n import t


def _more(key):
    st.session_state[key] = st.session_state.get(key, 10) + 10


def _transcripts(uid):
    total = db.count_history(uid)
    if not total:
        ui.empty_state(t("c.nothing"))
        return
    limit = st.session_state.get("hl_trans", 10)
    for it in db.list_history(uid, limit):
        with st.expander(f"{ui.fmt_ts(it['created_at'])} · {it['language_name']}"):
            st.text_area(t("t.transcript"), it["transcript"], height=140, disabled=True, key=f"h_t_{it['id']}", label_visibility="collapsed")
            a, b = st.columns(2, gap="small")
            with a:
                st.download_button(t("c.download"), it["transcript"].encode("utf-8"), file_name=f"transcript-{it['id']}.txt",
                                   mime="text/plain", key=f"gg_h_td_{it['id']}")
            with b:
                st.button(t("c.delete"), key=f"gs_h_tx_{it['id']}", on_click=db.delete_history_item, args=(uid, it["id"]))
    if total > limit:
        st.button(t("c.more"), key="gg_h_tmore", on_click=_more, args=("hl_trans",))
    with st.expander(t("c.delete_all")):
        st.button(t("c.delete_all"), key="gs_h_tclear", on_click=db.clear_history, args=(uid,))


def _speech(uid):
    total = db.count_tts(uid)
    if not total:
        ui.empty_state(t("c.nothing"))
        return
    limit = st.session_state.get("hl_tts", 10)
    for it in db.list_tts(uid, limit):
        with st.expander(f"{ui.fmt_ts(it['created_at'])} · {it['language_name']} · {it['voice']}"):
            st.text_area(t("t.speech_hist"), it["text"], height=110, disabled=True, key=f"h_s_{it['id']}", label_visibility="collapsed")
            if it["has_audio"] and st.toggle("▶", key=f"h_play_{it['id']}"):  # audio is loaded only when asked for
                audio, container = db.get_tts_audio(uid, it["id"])
                if audio:
                    mime = "audio/mpeg" if container == "mp3" else "audio/wav"
                    st.audio(audio, format=mime)
                    st.download_button(t("t.dl_audio"), audio, file_name=f"speech-{it['id']}.{container}", mime=mime, key=f"gg_h_sd_{it['id']}")
            st.button(t("c.delete"), key=f"gs_h_sx_{it['id']}", on_click=db.delete_tts, args=(uid, it["id"]))
    if total > limit:
        st.button(t("c.more"), key="gg_h_smore", on_click=_more, args=("hl_tts",))
    with st.expander(t("c.delete_all")):
        st.button(t("c.delete_all"), key="gs_h_sclear", on_click=db.clear_tts, args=(uid,))


def _open_conversation(conv_id):
    st.session_state["open_conv"] = conv_id
    st.switch_page(ui.PAGES["ask"])


def _conversations(uid):
    total = db.count_conversations(uid)
    if not total:
        ui.empty_state(t("c.nothing"))
        return
    limit = st.session_state.get("hl_conv", 10)
    for it in db.list_conversations(uid, limit):
        with st.expander(f"{ui.fmt_ts(it['updated_at'])} · {it['title']}"):
            for m in db.get_messages(uid, it["id"]):
                who = t("hi.you") if m["role"] == "user" else t("a.ai")
                kind = " (🎤)" if m.get("input_mode") in ("voice", "upload") else ""
                st.markdown(f"**{ui.esc(who)}{kind}**", unsafe_allow_html=True)
                st.markdown(ui.rtl_wrap(m["content"], m.get("language") or "english"), unsafe_allow_html=True)
                if m.get("raw_transcript") and m["raw_transcript"] != m["content"]:
                    st.caption(f'{t("t.transcript")}: {m["raw_transcript"]}')
            a, b = st.columns(2, gap="small")
            with a:
                if st.button(t("hi.continue"), key=f"gs_h_cc_{it['id']}"):
                    _open_conversation(it["id"])
            with b:
                st.button(t("c.delete"), key=f"gs_h_cx_{it['id']}", on_click=db.delete_conversation, args=(uid, it["id"]))
    if total > limit:
        st.button(t("c.more"), key="gg_h_cmore", on_click=_more, args=("hl_conv",))
    with st.expander(t("c.delete_all")):
        st.button(t("c.delete_all"), key="gs_h_cclear", on_click=db.clear_conversations, args=(uid,))


def history_page():
    user = ui.require_login()
    uid = user["id"]  # always from the server-side session, never from user input
    ui.page_header(t("hi.title"), "history")
    ui.language_selector("history")  # changing language never deletes anything
    tabs = st.tabs([t("hi.conv"), t("hi.trans"), t("hi.speech")])
    with tabs[0]:
        _conversations(uid)
    with tabs[1]:
        _transcripts(uid)
    with tabs[2]:
        _speech(uid)
