"""Weather from Open-Meteo for the farmer's saved location or searched place."""

from datetime import datetime

import streamlit as st

import database as db
import ui
import weather
from i18n import t


# Cache forecast results across Streamlit sessions in this app process.
@st.cache_data(ttl=1800, show_spinner=False)
def _cached_forecast(latitude, longitude):
    return weather.forecast(latitude, longitude)


# Cache geocoding results for 24 hours.
@st.cache_data(ttl=86400, show_spinner=False)
def _cached_geocode(name, state):
    return weather.geocode(name, state)


def _day_label(iso):
    try:
        return datetime.fromisoformat(iso).strftime("%a %d %b")
    except (ValueError, TypeError):
        return iso


def _show(place_label, lat, lon):
    try:
        data = _cached_forecast(float(lat), float(lon))
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
        c4.metric(
            t("w.rain"),
            f'{(day["precipitation_sum"][0] or 0):.1f} mm'
        )

    with st.container(key="card_weather_next"):
        ui.card_head("history", t("w.next"))

        cols = st.columns(min(4, len(day["time"])))

        for i, col in enumerate(cols):
            with col:
                st.markdown(f"**{_day_label(day['time'][i])}**")
                st.write(
                    f'{t("w.max")} '
                    f'{day["temperature_2m_max"][i]:.0f}° / '
                    f'{t("w.min")} '
                    f'{day["temperature_2m_min"][i]:.0f}°'
                )
                st.write(
                    f'{t("w.rain_chance")}: '
                    f'{(day["precipitation_probability_max"][i] or 0):.0f}%'
                )
                st.write(
                    f'💧 {(day["precipitation_sum"][i] or 0):.1f} mm'
                )

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

    # Search results take priority over the saved location.
    places = st.session_state.get("weather_places") or []

    if places:
        st.divider()

        idx = st.selectbox(
            t("w.pick"),
            range(len(places)),
            format_func=lambda i: places[i]["label"],
            key="weather_pick"
        )

        selected = places[idx]

        _show(
            selected["label"],
            selected["latitude"],
            selected["longitude"]
        )

        if st.button(t("w.clear"), key="weather_clear_search"):
            st.session_state.pop("weather_places", None)
            st.rerun()

    elif profile.get("latitude") is not None:
        place = (
            profile.get("place_name")
            or profile.get("district")
        )

        st.markdown(
            f'<p class="hint">{ui.esc(t("w.saved_place", place=place))}</p>',
            unsafe_allow_html=True
        )

        _show(
            place,
            profile["latitude"],
            profile["longitude"]
        )

    elif profile.get("district"):
        ui.notice("info", "", t("d.set_loc"))

    st.divider()

    with st.form("weather_search"):
        query = st.text_input(t("w.place"), max_chars=80)
        submitted = st.form_submit_button(
            t("w.search"),
            key="gp_weather_search"
        )

    if submitted:
        query = (query or "").strip()

        if len(query) < 2:
            ui.notice("warn", "", t("w.not_found"))
            st.session_state.pop("weather_places", None)
        else:
            try:
                places = _cached_geocode(
                    query,
                    profile.get("state") or ""
                )

                st.session_state["weather_places"] = places

                if not places:
                    ui.notice("warn", "", t("w.not_found"))

            except weather.WeatherError:
                ui.notice("warn", "", t("w.unavailable"))

        st.rerun()