"""Log in, Sign up, and Continue with Google (signed-out pages)."""

import logging

import streamlit as st

import database as db
import google_auth
import ui
from i18n import t
from styles import AUTH_CSS
from ui import notice

log = logging.getLogger("agrivoice.auth")
_warned = False


def _brand_panel():
    with st.container(key="auth_brand"):
        st.markdown(f"{ui.BRAND_MARK}<h2>{ui.esc(t('auth.hero'))}</h2><p>{ui.esc(t('app.tagline'))}</p>"
                    f"<p><b>GNANI AGRI VOICE</b></p>", unsafe_allow_html=True)


def _google_section() -> bool:
    """Shows Continue with Google only when it is fully configured. Nothing is shown otherwise."""
    global _warned
    if not google_auth.is_configured():
        if not _warned:
            _warned = True
            log.info("Continue with Google is hidden; missing settings: %s", ", ".join(google_auth.missing_settings()) or "Authlib")
        return False
    st.markdown(f'<div class="or-line">{ui.esc(t("auth.or"))}</div>', unsafe_allow_html=True)
    if st.button(t("auth.google"), key="gg_google"):
        st.login("google")
    return True


def login_page():
    if ui.current_user():
        st.switch_page(ui.PAGES["dashboard"])
    st.markdown(AUTH_CSS, unsafe_allow_html=True)
    left, right = st.columns(2, gap="large")
    with left:
        _brand_panel()
    with right:
        with st.container(key="card_auth"):
            ui.language_selector("login")
            st.markdown(f'<h1 class="auth-title">{ui.esc(t("auth.login"))}</h1>', unsafe_allow_html=True)
            ui.show_flash()
            with st.form("login_form"):
                email = st.text_input(t("auth.email"), autocomplete="email")
                password = st.text_input(t("auth.password"), type="password", autocomplete="current-password")
                submitted = st.form_submit_button(t("auth.login"), key="gp_login_submit")
            if submitted:
                user, error = db.authenticate(email, password)
                if error:
                    notice("error", t("auth.fail"), error)
                else:
                    ui.start_session(user)
                    st.rerun()
            _google_section()
            st.page_link(ui.PAGES["signup"], label=t("auth.to_signup"))


def signup_page():
    if ui.current_user():
        st.switch_page(ui.PAGES["dashboard"])
    st.markdown(AUTH_CSS, unsafe_allow_html=True)
    left, right = st.columns(2, gap="large")
    with left:
        _brand_panel()
    with right:
        with st.container(key="card_auth"):
            ui.language_selector("signup")
            st.markdown(f'<h1 class="auth-title">{ui.esc(t("auth.signup"))}</h1>', unsafe_allow_html=True)
            with st.form("signup_form"):
                name = st.text_input(t("auth.name"), autocomplete="name")
                email = st.text_input(t("auth.email"), autocomplete="email")
                password = st.text_input(t("auth.password"), type="password", autocomplete="new-password")
                confirm = st.text_input(t("auth.confirm"), type="password", autocomplete="new-password")
                submitted = st.form_submit_button(t("auth.signup"), key="gp_signup_submit")
            if submitted:
                if password != confirm:
                    notice("error", t("auth.mismatch"))
                else:
                    user, error = db.create_user(email, name, password, language=st.session_state.get("lang_id") or "english")
                    if error:
                        notice("error", t("auth.fail_signup"), error)
                    else:
                        st.session_state["flash"] = ("ok", t("auth.created"))
                        st.switch_page(ui.PAGES["login"])
            _google_section()
            st.page_link(ui.PAGES["login"], label=t("auth.to_login"))


def sync_google_login():
    """Called on every run. If Google has authenticated this browser, start (or refresh) our own session."""
    if ui.current_user():
        return
    claims = google_auth.identity()
    if claims is None:
        return
    ok, reason = google_auth.validate_claims(claims)
    if not ok:
        if reason != "expired":  # an old cookie just means "please sign in again", so stay quiet
            st.session_state["flash"] = ("error", "Google sign-in failed. Please try again.")
        st.logout()
        return
    user, error, note = db.sign_in_with_google(claims["sub"], claims["email"], claims["email_verified"], claims.get("name") or "")
    if error:
        st.logout()
        return
    ui.start_session(user)
    if note:
        st.session_state["flash"] = ("info", note)
