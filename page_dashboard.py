"""Home: welcome, Ask button, weather overview, my crop, shortcuts and recent conversations."""

import streamlit as st

import database as db
import ui
import weather
from data import agri_data as A
from i18n import t


def _go(page_key, **state):
    st.session_state.update(state)
    st.switch_page(ui.PAGES[page_key])


def _weather_card(profile):
    ui.card_head("cloud", t("d.weather"))
    if profile.get("latitude") is None:
        st.markdown(f'<p class="hint">{ui.esc(t("d.set_loc"))}</p>', unsafe_allow_html=True)
        if st.button(t("d.edit_farm"), key="gs_dash_loc"):
            _go("profile")
        return
    try:
        data = weather.forecast(profile["latitude"], profile["longitude"])
    except weather.WeatherError:
        ui.notice("warn", "", t("w.unavailable"))
        return
    cur, day = data["current"], data["daily"]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric(t("w.temp"), f'{cur["temperature_2m"]:.0f} °C')
    c2.metric(t("w.hum"), f'{cur["relative_humidity_2m"]:.0f} %')
    c3.metric(t("w.wind"), f'{cur["wind_speed_10m"]:.0f} km/h')
    c4.metric(t("w.rain"), f'{(day["precipitation_sum"][0] or 0):.1f} mm')
    st.markdown(f'<p class="hint">{ui.esc(t(weather.precaution_keys(data)[0]))}</p>', unsafe_allow_html=True)
    st.caption(f'{t("w.source")} · {profile.get("place_name") or ""}')


def dashboard_page():
    user = ui.require_login()
    profile = db.get_profile(user["id"])
    ui.page_header(t("d.welcome", name=user["display_name"].split()[0]), "sprout")
    st.markdown(f'<p class="hint">{ui.esc(t("d.sub"))}</p>', unsafe_allow_html=True)

    with st.container(key="card_dash_hero"):
        c1, c2 = st.columns([3, 2], vertical_alignment="bottom")
        with c1:
            if st.button("🎤  " + t("d.ask"), key="gp_dash_ask", use_container_width=True):
                _go("ask")
            st.caption(t("d.ask_hint"))
        with c2:
            ui.language_selector("dash")

    with st.container(key="card_dash_weather"):
        _weather_card(profile)

    with st.container(key="card_dash_crop"):
        ui.card_head("leaf", t("d.my_crops"))
        crop = profile.get("primary_crop")
        if crop:
            label = t(f"cp.{crop}") if crop in A.CROPS else crop
            where = ", ".join(x for x in (profile.get("district"), profile.get("state")) if x)
            st.markdown(f'<p style="font-size:1.25rem;margin:.2rem 0"><b>{ui.esc(label)}</b></p>'
                        f'<p class="hint">{ui.esc(where)}</p>', unsafe_allow_html=True)
        else:
            st.markdown(f'<p class="hint">{ui.esc(t("d.no_crop"))}</p>', unsafe_allow_html=True)
        if st.button(t("d.edit_farm"), key="gs_dash_edit"):
            _go("profile")

    st.markdown(f'<h3 style="margin-top:1.2rem">{ui.esc(t("d.services"))}</h3>', unsafe_allow_html=True)
    tiles = [("sprout", "d.s_crop", "d.s_crop_d", "crops", {"crop_topic": "general"}),
             ("bug", "d.s_disease", "d.s_disease_d", "health", {}),
             ("drop", "d.s_irr", "d.s_irr_d", "crops", {"crop_topic": "irrigation"}),
             ("flask", "d.s_fert", "d.s_fert_d", "crops", {"crop_topic": "fertilizer"}),
             ("bug", "d.s_pest", "d.s_pest_d", "crops", {"crop_topic": "pest"}),
             ("scroll", "d.s_scheme", "d.s_scheme_d", "schemes", {})]
    cols = st.columns(3)
    for i, (ic, title, desc, page, state) in enumerate(tiles):
        with cols[i % 3]:
            with st.container(key=f"card_tile_{i}"):
                st.markdown(f'<div class="card-head"><span class="chip">{ui.icon(ic)}</span><h3>{ui.esc(t(title))}</h3></div>'
                            f'<p class="hint">{ui.esc(t(desc))}</p>', unsafe_allow_html=True)
                if st.button(t("d.open"), key=f"gs_tile_{i}", use_container_width=True):
                    _go(page, **state)

    with st.container(key="card_dash_recent"):
        ui.card_head("history", t("d.recent"))
        convs = db.list_conversations(user["id"], 5)
        if not convs:
            st.markdown(f'<p class="hint">{ui.esc(t("d.none_recent"))}</p>', unsafe_allow_html=True)
        for c in convs:
            c1, c2 = st.columns([4, 1], vertical_alignment="center")
            c1.markdown(f'**{ui.esc(c["title"])}**  \n<span class="hint">{ui.fmt_ts(c["updated_at"])} · '
                        f'{ui.esc(t("d.messages", n=c["message_count"]))}</span>', unsafe_allow_html=True)
            if c2.button(t("d.open"), key=f"gs_recent_{c['id']}"):
                _go("ask", open_conv=c["id"])
