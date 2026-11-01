"""Help: short answers to common questions, in the farmer's language."""

import streamlit as st

import languages as L
import ui
from i18n import t


def help_page():
    ui.require_login()
    ui.page_header(t("he.title"), "help")
    ui.language_selector("help")
    voice_langs = ", ".join(l.native for l in L.app_languages() if L.voice_ready(l))
    with st.container(key="card_help"):
        for i in range(1, 6):
            with st.expander(t(f"he.q{i}"), expanded=(i == 1)):
                st.write(t(f"he.a{i}", voice_langs=voice_langs) if i == 2 else t(f"he.a{i}"))
        st.caption(t("c.disclaimer"))
