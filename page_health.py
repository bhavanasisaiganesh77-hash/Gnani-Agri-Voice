"""Plant Health Help: describe (type or speak) and/or photograph a crop problem and get POSSIBLE causes, signs to
check, safe next steps, prevention and when to call an expert. Never presented as a confirmed diagnosis."""

import hashlib
import io

import streamlit as st
from PIL import Image, UnidentifiedImageError

import agri_prompts as P
import agri_service
import audio_utils
import database as db
import languages as L
import llm_service
import stt_service
import ui
from chat_store import get_store
from data import agri_data as A
from i18n import t

MAX_IMAGE_BYTES = 5 * 1024 * 1024
MAX_EDGE = 1568  # longest side sent to the model; keeps requests small and fast
MAGIC = {b"\xff\xd8\xff": "jpeg", b"\x89PNG\r\n\x1a\n": "png"}


def prepare_image(data: bytes):
    """Return (jpeg_bytes, 'image/jpeg') or (None, error_key). Checks size, real file type and decodability,
    strips metadata (e.g. GPS) by re-encoding, and shrinks very large photos."""
    if len(data) > MAX_IMAGE_BYTES:
        return None, "h.img_big"
    if not any(data.startswith(sig) for sig in MAGIC):
        return None, "h.img_type"
    try:
        with Image.open(io.BytesIO(data)) as img:
            img.load()
            img = img.convert("RGB")
            img.thumbnail((MAX_EDGE, MAX_EDGE))
            out = io.BytesIO()
            img.save(out, format="JPEG", quality=88)  # re-encoding drops EXIF/GPS
        return out.getvalue(), "image/jpeg"
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError):
        return None, "h.img_type"


def _section(title_key, items, icon_name):
    if not items:
        return
    st.markdown(f'<h4>{ui.icon(icon_name, 18)} {ui.esc(t(title_key))}</h4>', unsafe_allow_html=True)
    for item in items:
        st.markdown(f"- {ui.esc(item)}", unsafe_allow_html=True)


def _render(result, lang_id):
    ui.notice("warn", "", t("h.banner"))
    if "parsed" in result:
        d = result["parsed"]
        if d["summary"]:
            st.markdown(ui.rtl_wrap(d["summary"], lang_id), unsafe_allow_html=True)
        _section("h.causes", d["possible_causes"], "help")
        _section("h.signs", d["signs_to_check"], "leaf")
        _section("h.steps", d["next_steps"], "sprout")
        _section("h.prevent", d["prevention"], "drop")
        if d["when_to_call_expert"]:
            st.markdown(f'<h4>{ui.esc(t("h.expert"))}</h4>', unsafe_allow_html=True)
            st.markdown(ui.rtl_wrap(d["when_to_call_expert"], lang_id), unsafe_allow_html=True)
        st.caption(f'{t("h.conf")} {"●○" if d["confidence"] == "low" else "●●"} '
                   f'({"low" if d["confidence"] == "low" else "medium"})')
    else:  # the model did not return the expected structure: show its text, still with the banner
        st.markdown(ui.rtl_wrap(result["raw"], lang_id), unsafe_allow_html=True)
    if result.get("had_image"):
        st.caption(t("h.photo_note"))
    if result.get("image_ignored"):
        ui.notice("info", "", t("h.no_image"))
    st.caption(t("c.disclaimer"))


def health_page():
    user = ui.require_login()
    lang = ui.current_language()
    profile = db.get_profile(user["id"])
    ui.page_header(t("h.title"), "bug")
    ui.notice("warn", "", t("h.banner"))

    crop_default = profile.get("primary_crop") if profile.get("primary_crop") in A.CROPS else "paddy"
    with st.container(key="card_health_form"):
        ui.language_selector("health")
        crop = st.selectbox(t("cr.crop"), list(A.CROPS), index=list(A.CROPS).index(crop_default),
                            format_func=lambda k: t(f"cp.{k}"), key="health_crop")
        other = st.text_input(t("cr.other_name"), max_chars=40, key="health_other") if crop == "other" else ""

        # optional: speak the symptoms (existing Gnani Prisma pipeline)
        if L.is_usable(lang, "stt") and ui.speech_ready():
            st.markdown(f'<p class="hint">{ui.esc(t("h.speak"))}</p>', unsafe_allow_html=True)
            gen = st.session_state.setdefault("health_gen", 0)
            audio = st.audio_input(t("h.speak"), key=f"health_mic_{gen}", label_visibility="collapsed")
            if audio is not None:
                data = audio.getvalue()
                digest = hashlib.sha256(data).hexdigest()
                if digest != st.session_state.get("health_hash") and ui.debounce("health_mic", digest):
                    st.session_state["health_hash"] = digest
                    error, _d, mime = audio_utils.validate_audio("health.wav", data)
                    if error:
                        ui.notice("error", *error)
                    else:
                        slot = st.empty()
                        ui.show_loading(slot, t("a.transcribing"))
                        text, err = stt_service.transcribe(data, "health.wav", mime, lang, itn=user["apply_itn"])
                        slot.empty()
                        if err:
                            ui.notice("error", *err)
                        else:
                            st.session_state["health_desc"] = text
                            st.session_state["health_gen"] = gen + 1
                            st.rerun()
        desc = st.text_area(t("h.desc"), key="health_desc", max_chars=1200, height=120, placeholder=t("h.ph"))
        photo = st.file_uploader(t("h.photo"), type=["jpg", "jpeg", "png"], key="health_photo", help=t("h.photo_hint"))
        st.caption(t("h.photo_hint"))
        go = st.button(t("h.go"), key="gp_health_go", use_container_width=True)

    if go:
        image = None
        if photo is not None:
            img_bytes, info = prepare_image(photo.getvalue())
            if img_bytes is None:
                ui.notice("error", "", t(info))
                return
            image = (img_bytes, info)
        if not desc.strip() and image is None:
            ui.notice("warn", "", t("h.need_input"))
            return
        crop_name = other.strip() if crop == "other" else A.CROPS[crop]
        request = P.disease_request(crop_name, desc.strip(), image is not None, lang.name)
        provider = llm_service.get_provider()
        slot = st.empty()
        ui.show_loading(slot, t("a.thinking"))
        try:
            raw = agri_service.one_shot(user["id"], request, lang, profile, image=image, provider=provider, max_tokens=1100)
        except agri_service.AnswerError as err:
            slot.empty()
            ui.notice("warn", t("a.limit") if err.kind == "rate_limit" else t("a.llm_down"))
            return
        slot.empty()
        parsed = P.parse_disease_json(raw)
        result = {"raw": raw, "had_image": image is not None and provider.supports_images,
                  "image_ignored": image is not None and not provider.supports_images}
        if parsed:
            result["parsed"] = parsed
        st.session_state["health_result"] = result
        st.session_state["health_result_lang"] = lang.id
        store = get_store(user, {})
        if store.persistent:  # the photo itself is never stored, only the text
            label = t(f"cp.{crop}") if crop != "other" else crop_name
            shown = (parsed["summary"] + "\n\n" + "\n".join(f"- {x}" for x in parsed["possible_causes"])) if parsed else raw
            store.add("user", f"{label}: {desc.strip() or '(photo)'}", lang, title=f"{t('h.title')}: {label}")
            store.add("assistant", shown, lang)

    if (res := st.session_state.get("health_result")):
        with st.container(key="card_health_result"):
            _render(res, st.session_state.get("health_result_lang", lang.id))
