"""GNANI AGRI VOICE - Voice-Powered Agricultural Assistant.
Your Voice. Your Language. Your Farming Assistant.

Launch this file: streamlit run streamlit_app.py
This file sets up the app and navigation; each page lives in its own file.
"""

from pathlib import Path

import streamlit as st

st.set_page_config(
    page_title="GNANI AGRI VOICE",
    page_icon="🌾",
    layout="wide",
    initial_sidebar_state="auto"
)

import database as db
import ui

from i18n import t
from page_account import profile_page, settings_page
from page_ask import ask_page
from page_auth import login_page, signup_page, sync_google_login
from page_crops import crops_page
from page_dashboard import dashboard_page
from page_health import health_page
from page_help import help_page
from page_history import history_page
from page_schemes import schemes_page
from page_stt import live_page, upload_page
from page_tts import tts_page
from page_weather import weather_page

# Import existing CSS and agricultural background function
from styles import BASE_CSS, set_agri_background


# Initialize database
@st.cache_resource
def _init_database():
    db.init_db()
    return True


_init_database()


# Application pages
P = st.Page

pages = {
    "login": P(
        login_page,
        title=t("nav.login"),
        icon=":material/login:",
        url_path="login",
        default=True
    ),

    "signup": P(
        signup_page,
        title=t("nav.signup"),
        icon=":material/person_add:",
        url_path="signup"
    ),

    "dashboard": P(
        dashboard_page,
        title=t("nav.dashboard"),
        icon=":material/home:",
        url_path="dashboard",
        default=True
    ),

    "ask": P(
        ask_page,
        title=t("nav.ask"),
        icon=":material/mic:",
        url_path="ask"
    ),

    "crops": P(
        crops_page,
        title=t("nav.crops"),
        icon=":material/agriculture:",
        url_path="crop-advice"
    ),

    "health": P(
        health_page,
        title=t("nav.health"),
        icon=":material/eco:",
        url_path="plant-health"
    ),

    "weather": P(
        weather_page,
        title=t("nav.weather"),
        icon=":material/cloud:",
        url_path="weather"
    ),

    "schemes": P(
        schemes_page,
        title=t("nav.schemes"),
        icon=":material/account_balance:",
        url_path="schemes"
    ),

    "history": P(
        history_page,
        title=t("nav.history"),
        icon=":material/history:",
        url_path="history"
    ),

    "live": P(
        live_page,
        title=t("nav.live"),
        icon=":material/graphic_eq:",
        url_path="live-speech-to-text"
    ),

    "upload": P(
        upload_page,
        title=t("nav.upload"),
        icon=":material/upload_file:",
        url_path="audio-upload"
    ),

    "tts": P(
        tts_page,
        title=t("nav.tts"),
        icon=":material/record_voice_over:",
        url_path="text-to-speech"
    ),

    "profile": P(
        profile_page,
        title=t("nav.profile"),
        icon=":material/person:",
        url_path="profile"
    ),

    "settings": P(
        settings_page,
        title=t("nav.settings"),
        icon=":material/settings:",
        url_path="settings"
    ),

    "help": P(
        help_page,
        title=t("nav.help"),
        icon=":material/help:",
        url_path="help"
    ),
}


# Update navigation pages
ui.PAGES.update(pages)


# Session and authentication
ui.enforce_session()
sync_google_login()


# Apply existing application CSS
st.markdown(BASE_CSS, unsafe_allow_html=True)


# Apply agricultural background
set_agri_background()


# Current logged-in user
user = ui.current_user()


if user:

    logo = Path(__file__).resolve().parent / "assets" / "logo.svg"

    if logo.exists():
        st.logo(str(logo), size="large")

    nav = st.navigation(
        {
            t("nav.sec_farm"): [
                pages[k]
                for k in (
                    "dashboard",
                    "ask",
                    "crops",
                    "health",
                    "weather",
                    "schemes",
                    "history"
                )
            ],

            t("nav.sec_tools"): [
                pages[k]
                for k in (
                    "live",
                    "upload",
                    "tts"
                )
            ],

            t("nav.sec_account"): [
                pages[k]
                for k in (
                    "profile",
                    "settings",
                    "help"
                )
            ],
        },
        position="sidebar",
    )

    with st.sidebar:

        st.markdown(
            f'<div class="user-card">'
            f'<span class="avatar">'
            f'{ui.esc(user["display_name"][:1].upper())}'
            f'</span>'
            f'<div class="who">'
            f'<b>{ui.esc(user["display_name"])}</b>'
            f'<small>{ui.esc(user["email"])}</small>'
            f'</div></div>',
            unsafe_allow_html=True
        )

        ui.language_selector("sidebar")

        if st.button(t("nav.signout"), key="gs_sidebar_signout"):
            ui.logout()

else:

    nav = st.navigation(
        [
            pages["login"],
            pages["signup"]
        ],
        position="hidden"
    )


# Run selected page
nav.run()