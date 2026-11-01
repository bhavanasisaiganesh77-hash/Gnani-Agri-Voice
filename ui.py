"""Shared building blocks used by every page: icons, notices, session handling, language selector, copy button."""

import html
import json
import logging
import os
import time
from datetime import datetime

import streamlit as st
import streamlit.components.v1 as components

import database as db
import languages as L
from i18n import m, t

esc = html.escape
log = logging.getLogger("agrivoice.ui")
_logged = set()
IDLE_TIMEOUT_SECONDS = int(os.getenv("SESSION_IDLE_MINUTES", "60")) * 60

# Filled in by streamlit_app.py so pages can link to each other: PAGES["tts"], PAGES["login"], ...
PAGES = {}

# ------------------------------------------------------------------------------ icons (Lucide style, 24x24, 2px round stroke)
_PATHS = {
    "mic": '<rect x="9" y="3" width="6" height="12" rx="3"/><path d="M5 11a7 7 0 0 0 14 0M12 18v3"/>',
    "upload": '<path d="M12 16V4M7 9l5-5 5 5M4 20h16"/>',
    "volume": '<path d="M11 5 6 9H2v6h4l5 4V5z"/><path d="M15.5 8.5a5 5 0 0 1 0 7M19 5a9 9 0 0 1 0 14"/>',
    "history": '<path d="M3 12a9 9 0 1 0 3-6.7L3 8"/><path d="M3 3v5h5M12 7v5l3 2"/>',
    "user": '<circle cx="12" cy="8" r="4"/><path d="M4 21a8 8 0 0 1 16 0"/>',
    "wave": '<path d="M4 10v4M8 6v12M12 3v18M16 7v10M20 10v4"/>',
    "sprout": '<path d="M7 20h10M12 20V10"/><path d="M12 10c0-4 3-6 7-6 0 4-3 6-7 6zM12 13c0-3-2-5-6-5 0 3 2 5 6 5z"/>',
    "cloud": '<path d="M17.5 19H9a7 7 0 1 1 6.71-9h1.79a4.5 4.5 0 1 1 0 9z"/>',
    "drop": '<path d="M12 22a7 7 0 0 0 7-7c0-2-1-3.9-3-5.5s-3.5-4-4-6.5c-.5 2.5-2 4.9-4 6.5C6 11.1 5 13 5 15a7 7 0 0 0 7 7z"/>',
    "flask": '<path d="M10 2v7.5L4.5 19a2 2 0 0 0 1.8 3h11.4a2 2 0 0 0 1.8-3L14 9.5V2M8.5 2h7M7 16h10"/>',
    "bug": '<path d="M9 7.1V6a3 3 0 1 1 6 0v1.1M8 2l1.9 1.9M16 2l-1.9 1.9"/><path d="M12 20c-3.3 0-6-2.7-6-6v-3a4 4 0 0 1 4-4h4a4 4 0 0 1 4 4v3c0 3.3-2.7 6-6 6zM12 20v-9M3 13h3M18 13h3M4 6c0 2 1.5 3.5 3 4M20 6c0 2-1.5 3.5-3 4"/>',
    "scroll": '<path d="M8 21h12a2 2 0 0 0 2-2v-2H10v2a2 2 0 1 1-4 0V5a2 2 0 1 0-4 0v3h4"/><path d="M19 17V5a2 2 0 0 0-2-2H4"/>',
    "chat": '<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>',
    "leaf": '<path d="M11 20A7 7 0 0 1 9.8 6.1C15.5 5 17 4.5 19 2c1 2 2 4.2 2 8 0 5.5-4.8 10-10 10z"/><path d="M2 21c0-3 1.9-5.4 5.1-6C9.5 14.5 12 13 13 12"/>',
    "help": '<circle cx="12" cy="12" r="10"/><path d="M9.1 9a3 3 0 0 1 5.8 1c0 2-3 3-3 3M12 17h.01"/>',
}


def icon(name: str, size: int = 22) -> str:
    return (f'<svg viewBox="0 0 24 24" width="{size}" height="{size}" fill="none" stroke="currentColor" stroke-width="2" '
            f'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{_PATHS[name]}</svg>')


BRAND_MARK = f'<span class="brand-mark" style="color:#fff">{icon("sprout", 26)}</span>'
LOADING = ('<div class="loading" role="status" aria-live="polite"><div class="bars"><span></span><span></span><span></span>'
           '<span></span><span></span></div><b>{title}</b></div>')


# ------------------------------------------------------------------------------ small components
def notice(kind, title, detail=""):
    st.markdown(f'<div class="notice {kind}" role="alert"><b>{esc(m(title))}</b>{esc(m(detail))}</div>', unsafe_allow_html=True)


def pill(text, kind="idle"):
    st.markdown(f'<span class="pill {kind}">{esc(text)}</span>', unsafe_allow_html=True)


def card_head(icon_name, title):
    st.markdown(f'<div class="card-head"><span class="chip">{icon(icon_name)}</span><h3>{esc(title)}</h3></div>', unsafe_allow_html=True)


def page_header(title, icon_name=None):
    chip = f'<span class="chip">{icon(icon_name)}</span>' if icon_name else ""
    st.markdown(f'<div class="page-head">{chip}<h1 class="page-title">{esc(title)}</h1></div>', unsafe_allow_html=True)


def show_loading(slot, title):
    slot.markdown(LOADING.format(title=esc(title)), unsafe_allow_html=True)


def empty_state(text):
    st.markdown(f'<div class="empty">{esc(text)}</div>', unsafe_allow_html=True)


def show_flash():
    flash = st.session_state.pop("flash", None)
    if flash:
        notice(*flash)


def fmt_ts(iso):
    try:
        return datetime.fromisoformat(iso).astimezone().strftime("%d-%m-%Y, %I:%M %p")
    except Exception:
        return iso


def copy_button(text, disabled, aria_label, label="Copy Transcript", copied="Copied to clipboard"):
    """Glass copy button. It reads the live text box, so unsaved edits are copied too."""
    template = """
<link href="https://fonts.googleapis.com/css2?family=Figtree:wght@600&display=swap" rel="stylesheet">
<style>
  html,body{margin:0;background:transparent}
  button{width:100%;height:46px;border-radius:14px;font:600 15.5px 'Figtree',system-ui,sans-serif;color:#fff;cursor:pointer;
    border:1px solid rgba(255,255,255,.5);background:linear-gradient(135deg,rgba(27,94,32,.96),rgba(20,71,26,.97));
    box-shadow:0 12px 26px -12px rgba(20,71,26,.75),inset 0 1px 0 rgba(255,255,255,.38);transition:transform .18s,filter .18s}
  button:hover:not(:disabled){transform:translateY(-1px);filter:brightness(1.07)}
  button:active:not(:disabled){transform:scale(.985)}
  button:disabled{opacity:.5;cursor:not-allowed;box-shadow:none}
  button:focus-visible{outline:3px solid #81C784;outline-offset:2px}
  @media (prefers-reduced-motion:reduce){button{transition:none}}
</style>
<button id="b" __DISABLED__>__LABEL_TEXT__</button>
<script>
  const fallback = __TEXT__;
  const btn = document.getElementById('b');
  const idle = btn.textContent;
  function currentText(){
    try{ const ta = window.parent.document.querySelector('textarea[aria-label=__LABEL__]'); if(ta) return ta.value; }catch(e){}
    return fallback;
  }
  async function copy(t){
    try{ await navigator.clipboard.writeText(t); return true; }
    catch(e){
      const a=document.createElement('textarea'); a.value=t; document.body.appendChild(a); a.select();
      let ok=false; try{ ok=document.execCommand('copy'); }catch(_){} a.remove(); return ok;
    }
  }
  btn.addEventListener('click', async ()=>{
    const ok = await copy(currentText());
    btn.textContent = ok ? __COPIED__ : '✕';
    setTimeout(()=>{ btn.textContent = idle; }, 1800);
  });
</script>
"""
    safe = lambda s: json.dumps(s).replace("</", "<\\/")
    page_html = (template.replace("__TEXT__", safe(text)).replace("__LABEL__", safe(aria_label))
                 .replace("__COPIED__", safe(copied)).replace("__LABEL_TEXT__", esc(label)).replace("__DISABLED__", "disabled" if disabled else ""))
    if hasattr(st, "iframe"):  # newer Streamlit: components.html is deprecated in favour of st.iframe
        st.iframe(page_html, height=50)
    else:
        components.html(page_html, height=50)


# ------------------------------------------------------------------------------ session
def current_user():
    return st.session_state.get("user")


def start_session(user):
    st.session_state.clear()
    st.session_state["lang_id"] = user["default_language"]  # restore the farmer's saved language
    st.session_state["user"] = user
    st.session_state["auth_version"] = user["auth_version"]
    st.session_state["last_active"] = time.time()


def logout(message="You have been logged out."):  # message may be an English text from i18n "msg"
    from google_auth import identity
    was_google = identity() is not None
    lang_id = st.session_state.get("lang_id")
    st.session_state.clear()
    if lang_id:
        st.session_state["lang_id"] = lang_id  # the sign-in screen stays in the language they were using
    st.session_state["flash"] = ("info", message)
    if was_google:
        st.logout()  # clears Streamlit's Google identity cookie, otherwise the next run would sign in again
    else:
        st.rerun()


def enforce_session():
    """Expire idle sessions, and sign out sessions invalidated by a password change or account removal."""
    user = current_user()
    if not user:
        return
    now = time.time()
    if now - st.session_state.get("last_active", now) > IDLE_TIMEOUT_SECONDS:
        logout("Your session expired because it was idle. Log in again to continue.")
    st.session_state["last_active"] = now
    fresh = db.get_user(user["id"])
    if fresh is None:
        logout("This account no longer exists.")
    if fresh["auth_version"] != st.session_state.get("auth_version"):
        logout("Your sign-in details changed, so you were signed out. Log in again.")
    st.session_state["user"] = fresh


def require_login():
    user = current_user()
    if not user:
        st.session_state["flash"] = ("info", t("c.login_needed"))
        st.switch_page(PAGES["login"])
        st.stop()
    return user


def speech_ready() -> bool:
    """True when speech services are configured. If not, the problem goes to the server log, not the screen."""
    from gnani_client import get_api_key
    ok = bool(get_api_key())
    if not ok and "gnani" not in _logged:
        _logged.add("gnani")
        log.error("GNANI_API_KEY is not set; speech features are disabled.")
    return ok


def unavailable():
    notice("error", t("c.unavailable_title"), t("c.unavailable_detail"))


# ------------------------------------------------------------------------------ duplicate-click guard
def debounce(name: str, fingerprint, seconds: float = 8.0) -> bool:
    """True if the action should run. The same input submitted again within a few seconds is ignored,
    so double clicks never trigger two paid API calls."""
    now = time.time()
    last = st.session_state.get(f"_debounce_{name}")
    if last and last[0] == fingerprint and now - last[1] < seconds:
        return False
    st.session_state[f"_debounce_{name}"] = (fingerprint, now)
    return True


# ------------------------------------------------------------------------------ language picker (central config)
def language_picker(page_key: str, capability: str):
    """Searchable selector for one capability. Returns (language, usable).

    Unavailable languages stay visible and labelled, and block the action.
    """
    user = current_user()
    langs = L.languages_for(capability)
    ids = [l.id for l in langs]
    current = st.session_state.get("lang_id") or user["default_language"]
    index = ids.index(current) if current in ids else 0
    chosen = st.selectbox(t("c.language"), ids, index=index,
                          format_func=lambda i: L.label(L.get_language(i), capability), key=f"{page_key}_lang")
    lang = L.get_language(chosen)
    usable = L.is_usable(lang, capability)
    if not usable:
        notice("warn", t("t.na", lang=lang.native))
    return lang, usable


# ------------------------------------------------------------------------------ app language selector
def _on_language_change(key):
    chosen = st.session_state.get(key)
    if chosen not in L.APP_LANGUAGE_IDS:
        return
    st.session_state["lang_id"] = chosen
    user = current_user()
    if user:  # remembered for next login; conversations are untouched
        db.set_language(user["id"], chosen)


def current_language() -> "L.Language":
    return L.get_language(st.session_state.get("lang_id") or L.DEFAULT_UI_LANGUAGE_ID)


def language_selector(where: str):
    """The farmer's language, in native scripts, with a clear marker where voice is not available.
    Used on every main screen; all selectors stay in sync because they are rebuilt from session state on each run."""
    key = f"lang_sel_{where}"
    st.session_state[key] = st.session_state.get("lang_id") or L.DEFAULT_UI_LANGUAGE_ID
    st.selectbox(t("c.language"), L.APP_LANGUAGE_IDS, key=key,
                 format_func=lambda i: L.app_label(L.get_language(i), t("c.voice_na")),
                 on_change=_on_language_change, args=(key,))
    lang = current_language()
    from i18n import has_ui
    if not has_ui(lang.id):
        notice("info", "", t("c.ui_fallback", lang=lang.name))


def rtl_wrap(text: str, lang_id: str) -> str:
    """Escaped text in a block with the right reading direction (for Urdu)."""
    direction = "rtl" if L.is_rtl(lang_id) else "auto"
    return f'<div dir="{direction}">{esc(text).replace(chr(10), "<br>")}</div>'
