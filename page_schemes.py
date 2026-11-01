"""Government schemes from data/schemes.json (official sources), each with its last-verified date."""

import streamlit as st

import agri_prompts as P
import agri_service
import schemes
import ui
from i18n import t


def schemes_page():
    user = ui.require_login()
    lang = ui.current_language()
    ui.page_header(t("sc.title"), "scroll")
    st.markdown(f'<p class="hint">{ui.esc(t("sc.intro"))}</p>', unsafe_allow_html=True)
    ui.language_selector("schemes")

    items = schemes.load()
    if not items:
        ui.unavailable()
        return
    sid = st.selectbox(t("sc.pick"), [s["id"] for s in items], format_func=lambda i: schemes.get(i)["name"], key="scheme_pick")
    s = schemes.get(sid)

    with st.container(key="card_scheme"):
        ui.card_head("scroll", s["name"])
        for title_key, value in (("sc.elig", s["eligibility"]), ("sc.benefit", s["benefits"])):
            st.markdown(f'<h4>{ui.esc(t(title_key))}</h4><p>{ui.esc(value)}</p>', unsafe_allow_html=True)
        st.markdown(f'<h4>{ui.esc(t("sc.docs"))}</h4>', unsafe_allow_html=True)
        for doc in s["documents"]:
            st.markdown(f"- {ui.esc(doc)}", unsafe_allow_html=True)
        st.link_button(t("sc.apply") + " ↗", s["official_url"])
        if s.get("last_verified"):
            st.caption(t("sc.verified", date=s["last_verified"]))
            if s.get("verified_note"):
                st.caption(s["verified_note"])
        else:
            ui.notice("warn", "", t("sc.unverified"))

    if lang.id != "english" and st.button(t("sc.explain"), key=f"gp_scheme_explain"):
        slot = st.empty()
        ui.show_loading(slot, t("a.thinking"))
        try:
            text = agri_service.one_shot(user["id"], P.scheme_explain_request(s, lang.name), lang, {}, max_tokens=500)
        except agri_service.AnswerError as err:
            slot.empty()
            ui.notice("warn", t("a.limit") if err.kind == "rate_limit" else t("a.llm_down"))
        else:
            slot.empty()
            with st.container(key="card_scheme_ai"):
                st.markdown(ui.rtl_wrap(text, lang.id), unsafe_allow_html=True)
                st.caption(t("sc.explain_note"))
