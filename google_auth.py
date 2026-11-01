"""Continue with Google, using Streamlit's built-in OpenID Connect login.

How it works (all server-side, nothing secret reaches the browser):
  1. st.login("google") sends the user to Google. Streamlit creates and checks the OAuth `state` and
     `nonce` values and exchanges the code for an ID token using your client secret.
  2. Streamlit validates the ID token's signature through the provider metadata (Authlib) and exposes the
     claims in st.user. It does NOT check the token's expiry, so we do (see validate_claims).
  3. We map the verified Google identity (the permanent `sub` plus a verified email) to a local account in
     database.sign_in_with_google, then start our own session.

Credentials live in .streamlit/secrets.toml (never in source code, and git-ignored).
"""

import time

import streamlit as st

GOOGLE_ISSUERS = ("https://accounts.google.com", "accounts.google.com")
# Only the exact placeholder text from secrets.toml.example counts as "not filled in yet".
_PLACEHOLDER_STARTS = ("your-", "your_", "paste-", "paste_", "changeme")


def _auth_section():
    try:
        return st.secrets.get("auth")
    except Exception:  # no secrets.toml at all
        return None


def _real(value) -> bool:
    if not value or not isinstance(value, str):
        return False
    v = value.strip().lower()
    return not (v.startswith(_PLACEHOLDER_STARTS) or "<" in v)


def missing_settings() -> list:
    """Which secrets are missing or still placeholders, as '[auth] name' strings (never the values)."""
    auth = _auth_section()
    google = (auth.get("google") if auth else None) or {}
    wanted = [("[auth] redirect_uri", (auth or {}).get("redirect_uri")),
              ("[auth] cookie_secret", (auth or {}).get("cookie_secret")),
              ("[auth.google] client_id", google.get("client_id")),
              ("[auth.google] client_secret", google.get("client_secret")),
              ("[auth.google] server_metadata_url", google.get("server_metadata_url"))]
    return [name for name, value in wanted if not _real(value)]


def authlib_installed() -> bool:
    try:
        import authlib  # noqa: F401
        return True
    except Exception:
        return False


def is_configured() -> bool:
    return not missing_settings() and authlib_installed()


def client_id():
    auth = _auth_section()
    return ((auth or {}).get("google") or {}).get("client_id")


def identity():
    """The Google claims for the currently authenticated browser, or None."""
    try:
        if not getattr(st.user, "is_logged_in", False):
            return None
        return {k: st.user.get(k) for k in ("iss", "sub", "email", "email_verified", "name", "exp", "aud")}
    except Exception:
        return None


def validate_claims(claims: dict):
    """Return (ok, reason). Reasons: 'expired' (quiet), or a human-readable message."""
    exp = claims.get("exp")
    try:
        if exp is not None and float(exp) <= time.time():
            return False, "expired"
    except (TypeError, ValueError):
        return False, "Google sent an unreadable sign-in token."
    if claims.get("iss") not in GOOGLE_ISSUERS:
        return False, "The sign-in token did not come from Google."
    aud, cid = claims.get("aud"), client_id()
    if cid and aud:
        auds = aud if isinstance(aud, (list, tuple)) else [aud]
        if cid not in auds:
            return False, "The sign-in token was issued for a different application."
    if not claims.get("sub"):
        return False, "Google did not return an account identifier."
    return True, ""
