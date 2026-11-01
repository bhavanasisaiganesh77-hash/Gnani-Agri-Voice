"""My Farm & Profile (farm details used for weather and context-aware advice) and Settings."""

import streamlit as st

import database as db
import ui
import weather
from data import agri_data as A
from i18n import t
from ui import notice


def profile_page():
    user = ui.require_login()
    ui.page_header(t("p.title"), "user")
    profile = db.get_profile(user["id"])

    with st.container(key="card_profile"):
        st.markdown(
            f'<div class="user-card plain"><span class="avatar big">{ui.esc(user["display_name"][:1].upper())}</span>'
            f'<div class="who"><b class="big">{ui.esc(user["display_name"])}</b><small>{ui.esc(user["email"])}</small></div></div>',
            unsafe_allow_html=True)
        ui.language_selector("profile")

    with st.container(key="card_farm"):
        ui.card_head("sprout", t("p.farm"))
        with st.form("farm_form"):
            states = [""] + A.STATES
            state = st.selectbox(t("p.state"), states, index=states.index(profile["state"]) if profile.get("state") in states else 0)
            district = st.text_input(t("p.district"), value=profile.get("district") or "", max_chars=60)
            crops = [""] + list(A.CROPS)
            current = profile.get("primary_crop") or ""
            crop = st.selectbox(t("p.crop"), crops, index=crops.index(current) if current in crops else 0,
                                format_func=lambda k: t(f"cp.{k}") if k else "—")
            size = st.number_input(t("p.size"), min_value=0.0, max_value=100000.0, step=0.5, format="%.1f",
                                   value=float(profile["farm_size"]) if profile.get("farm_size") else 0.0)
            saved = st.form_submit_button(t("p.save"), key="gp_farm_save")
        if saved:
            lat = lon = place = None
            if district.strip():  # turn the district into real coordinates for Open-Meteo
                try:
                    found = weather.geocode(district.strip(), state)
                    if found:
                        lat, lon, place = found[0]["latitude"], found[0]["longitude"], found[0]["label"]
                except weather.WeatherError:
                    found = None
            db.save_profile(user["id"], state, district, crop, size or None, lat, lon, place)
            st.toast(t("p.saved"))
            if place:
                notice("ok", "", t("p.loc_found", place=place))
            elif district.strip():
                notice("warn", "", t("p.loc_nf"))
        elif profile.get("place_name"):
            st.caption(t("p.loc_found", place=profile["place_name"]))

    if st.button(t("nav.signout"), key="gs_profile_logout"):
        ui.logout()


def settings_page():
    user = ui.require_login()
    ui.page_header(t("s.title"), "user")

    with st.container(key="card_set_lang"):
        st.subheader(t("s.lang"))
        ui.language_selector("settings")

    with st.container(key="card_set_name"):
        st.subheader(t("p.name"))
        with st.form("name_form"):
            new_name = st.text_input(t("p.name"), value=user["display_name"])
            if st.form_submit_button(t("c.save"), key="gp_set_name"):
                error = db.update_display_name(user["id"], new_name)
                if error:
                    notice("error", t("s.name_not_saved"), error)
                else:
                    st.rerun()

    with st.container(key="card_set_prefs"):
        with st.form("prefs_form"):
            pref_voice = st.toggle(t("s.voice"), value=user["voice_reply"])
            pref_hist = st.toggle(t("s.save_hist"), value=user["save_history"])
            pref_itn = st.toggle(t("s.itn"), value=user["apply_itn"])
            if st.form_submit_button(t("c.save"), key="gp_set_prefs"):
                # the language is saved the moment it is changed; this form only keeps the other preferences
                db.update_preferences(user["id"], user["default_language"], pref_hist, pref_itn)
                db.set_voice_reply(user["id"], pref_voice)
                st.toast(t("c.saved"))
                st.rerun()

    if user["has_password"]:
        with st.container(key="card_set_pw"):
            st.subheader(t("s.pw"))
            with st.form("pw_form", clear_on_submit=True):
                cur = st.text_input(t("s.pw_cur"), type="password", autocomplete="current-password")
                new = st.text_input(t("s.pw_new"), type="password", autocomplete="new-password")
                conf = st.text_input(t("s.pw_conf"), type="password", autocomplete="new-password")
                if st.form_submit_button(t("s.pw"), key="gp_set_pw"):
                    if new != conf:
                        notice("error", t("auth.mismatch"))
                    else:
                        error = db.change_password(user["id"], cur, new)
                        if error:
                            notice("error", t("s.pw"), error)
                        else:
                            ui.logout(t("s.pw_done"))
    else:
        st.caption(t("s.google_only"))

    with st.expander(t("s.del")):
        with st.form("delete_form"):
            pw = confirm = ""
            if user["has_password"]:
                pw = st.text_input(t("auth.password"), type="password", autocomplete="current-password")
            else:
                confirm = st.text_input("DELETE")
            sure = st.checkbox(t("s.del_confirm"))
            if st.form_submit_button(t("s.del"), key="gs_set_delete"):
                if not sure:
                    notice("warn", t("s.del_tick"))
                else:
                    error = db.delete_user(user["id"], pw, confirm)
                    if error:
                        notice("error", t("s.del"), error)
                    else:
                        ui.logout(t("s.del_done"))
