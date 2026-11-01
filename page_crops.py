"""Crop Advice: a short form (crop, stage, place, soil, water, symptoms) -> practical advice in the farmer's language."""

import streamlit as st

import agri_prompts as P
import agri_service
import database as db
import gnani_client as G
import languages as L
import tts_service
import ui
from chat_store import get_store
from data import agri_data as A
from i18n import t


def _speak(lang, text, user, key):
    if not (L.is_usable(lang, "tts") and ui.speech_ready()):
        return
    cache = st.session_state.setdefault("crops_audio", {})
    if key not in cache and st.button(t("a.listen"), key=f"gs_crop_listen"):
        slot = st.empty()
        ui.show_loading(slot, t("a.speaking"))
        try:
            cache[key] = tts_service.speak(text, lang)[0]
        except G.GnaniError:
            ui.notice("warn", t("a.voice_fail"))
        slot.empty()
    if key in cache:
        st.audio(cache[key], format="audio/wav")


def crops_page():
    user = ui.require_login()
    lang = ui.current_language()
    profile = db.get_profile(user["id"])
    ui.page_header(t("cr.title"), "sprout")
    st.markdown(f'<p class="hint">{ui.esc(t("cr.intro"))}</p>', unsafe_allow_html=True)

    topic_default = st.session_state.pop("crop_topic", None)
    if topic_default in A.TOPICS:
        st.session_state["crops_topic"] = topic_default
    crop_default = profile.get("primary_crop") if profile.get("primary_crop") in A.CROPS else "paddy"
    state_default = profile.get("state") if profile.get("state") in A.STATES else None

    with st.container(key="card_crops_form"):
        ui.language_selector("crops")
        if profile.get("primary_crop") or profile.get("state"):
            st.caption(t("cr.filled"))
        topic = st.radio(t("cr.topic"), A.TOPICS, format_func=lambda k: t(f"tp.{k}"), horizontal=True, key="crops_topic")
        c1, c2 = st.columns(2)
        crop = c1.selectbox(t("cr.crop"), list(A.CROPS), index=list(A.CROPS).index(crop_default),
                            format_func=lambda k: t(f"cp.{k}"), key="crops_crop")
        stage = c2.selectbox(t("cr.stage"), list(A.STAGES), index=1, format_func=lambda k: t(f"stage.{k}"), key="crops_stage")
        other = st.text_input(t("cr.other_name"), max_chars=40, key="crops_other") if crop == "other" else ""
        c3, c4 = st.columns(2)
        state = c3.selectbox(t("cr.state"), [""] + A.STATES, index=([""] + A.STATES).index(state_default) if state_default else 0,
                             key="crops_state")
        district = c4.text_input(t("cr.district"), value=profile.get("district") or "", max_chars=60, key="crops_district")
        c5, c6 = st.columns(2)
        soil = c5.selectbox(t("cr.soil"), list(A.SOILS), format_func=lambda k: t(f"soil.{k}"), key="crops_soil")
        water = c6.selectbox(t("cr.water"), list(A.WATER), format_func=lambda k: t(f"wat.{k}"), key="crops_water")
        symptoms = st.text_area(t("cr.symptoms"), max_chars=600, height=90, key="crops_symptoms")
        go = st.button(t("cr.get"), key="gp_crops_go", use_container_width=True)

    if go:
        if crop == "other" and not other.strip():
            ui.notice("warn", t("cr.need_crop"))
        else:
            crop_name = other.strip() if crop == "other" else A.CROPS[crop]
            form = {"topic": topic, "crop": crop_name, "stage": A.STAGES[stage], "state": state, "district": district.strip(),
                    "soil": A.SOILS[soil], "water": A.WATER[water], "symptoms": symptoms.strip()}
            request = P.advisory_request(form)
            slot = st.empty()
            ui.show_loading(slot, t("a.thinking"))
            try:
                text = agri_service.one_shot(user["id"], request, lang, profile)
            except agri_service.AnswerError as err:
                slot.empty()
                ui.notice("warn", t("a.limit") if err.kind == "rate_limit" else t("a.llm_down"))
            else:
                slot.empty()
                label = t(f"cp.{crop}") if crop != "other" else crop_name
                saved = False
                store = get_store(user, {})  # a one-off record; does not disturb the open chat
                if store.persistent:
                    store.add("user", request, lang, title=f"{t(f'tp.{topic}')}: {label}")
                    store.add("assistant", text, lang)
                    saved = True
                st.session_state["crops_result"] = {"title": t("cr.result", crop=label), "text": text, "saved": saved,
                                                    "key": hash((request, text)), "lang": lang.id}

    res = st.session_state.get("crops_result")
    if res:
        with st.container(key="card_crops_result"):
            ui.card_head("leaf", res["title"])
            st.markdown(ui.rtl_wrap(res["text"], res["lang"]), unsafe_allow_html=True)
            _speak(lang, res["text"], user, res["key"])
            if res["saved"]:
                st.caption(t("cr.saved"))
            st.caption(t("c.disclaimer"))
