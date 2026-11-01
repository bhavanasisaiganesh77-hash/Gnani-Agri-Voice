"""Weather from Open-Meteo for the farmer's saved location (or any place they search), with farming precautions."""

from datetime import datetime

import streamlit as st

import database as db
import ui
import weather
from i18n import t


def _day_label(iso):
    try:
        return datetime.fromisoformat(iso).strftime("%a %d %b")
    except ValueError:
        return iso


def _show(place_label, lat, lon):
    try:
        data = weather.forecast(lat, lon)
    except weather.WeatherError:
        ui.notice("warn", "", t("w.unavailable"))
        return
    cur, day = data["current"], data["daily"]
    with st.container(key="card_weather_now"):
        ui.card_head("cloud", f'{t("w.now")} · {place_label}')
        c1, c2, c3, c4 = st.columns(4)
        c1.metric(t("w.temp"), f'{cur["temperature_2m"]:.0f} °C')
        c2.metric(t("w.hum"), f'{cur["relative_humidity_2m"]:.0f} %')
        c3.metric(t("w.wind"), f'{cur["wind_speed_10m"]:.0f} km/h')
        c4.metric(t("w.rain"), f'{(day["precipitation_sum"][0] or 0):.1f} mm')
    with st.container(key="card_weather_next"):
        ui.card_head("history", t("w.next"))
        cols = st.columns(min(4, len(day["time"])))
        for i, col in enumerate(cols):
            with col:
                st.markdown(f"**{_day_label(day['time'][i])}**")
                st.write(f'{t("w.max")} {day["temperature_2m_max"][i]:.0f}° / {t("w.min")} {day["temperature_2m_min"][i]:.0f}°')
                st.write(f'{t("w.rain_chance")}: {(day["precipitation_probability_max"][i] or 0):.0f}%')
                st.write(f'💧 {(day["precipitation_sum"][i] or 0):.1f} mm')
    with st.container(key="card_weather_advice"):
        ui.card_head("leaf", t("w.advice"))
        for key in weather.precaution_keys(data):
            st.markdown(f"- {ui.esc(t(key))}", unsafe_allow_html=True)
        st.caption(t("w.source"))


def weather_page():
    user = ui.require_login()
    profile = db.get_profile(user["id"])
    ui.page_header(t("w.title"), "cloud")
    ui.language_selector("weather")

    if profile.get("latitude") is not None:
        st.markdown(f'<p class="hint">{ui.esc(t("w.saved_place", place=profile.get("place_name") or profile["district"]))}</p>',
                    unsafe_allow_html=True)
        _show(profile.get("place_name") or profile["district"], profile["latitude"], profile["longitude"])
        st.divider()
    elif profile.get("district"):
        ui.notice("info", "", t("d.set_loc"))

    with st.form("weather_search"):
        query = st.text_input(t("w.place"), max_chars=80)
        submitted = st.form_submit_button(t("w.search"), key="gp_weather_search")
    if submitted:
        try:
            places = weather.geocode(query, profile.get("state") or "")
        except weather.WeatherError:
            ui.notice("warn", "", t("w.unavailable"))
            return
        if not places:
            ui.notice("warn", "", t("w.not_found"))
        st.session_state["weather_places"] = places
    places = st.session_state.get("weather_places") or []
    if places:
        idx = st.selectbox(t("w.pick"), range(len(places)), format_func=lambda i: places[i]["label"], key="weather_pick")
        p = places[idx]
        _show(p["label"], p["latitude"], p["longitude"])
