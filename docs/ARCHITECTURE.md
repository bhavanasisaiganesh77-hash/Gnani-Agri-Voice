# Architecture report (Phase 1) and what the upgrade changed

## Existing application (Gnani Voice Studio) – as inspected
Streamlit app, ~20 Python modules, one commit, SQLite.

| Module | Role | Decision |
|---|---|---|
| `database.py` | SQLite: users, sign-in identities, history, tts_history, conversations/messages, versioned migrations with automatic backup, lockout, hashing | **Kept**, migrated v2 → v3 |
| `google_auth.py`, `page_auth.py` | Email/password + Google (Streamlit OIDC) | **Kept**, localized |
| `gnani_client.py`, `audio_utils.py`, `voices.py`, `languages.py` | Prisma STT / Timbre TTS REST client, validation, voices, language table | **Kept**; STT got optional `model`; audio limit fixed to 30 s |
| `page_stt.py`, `page_tts.py` | Speak Live, Record/Upload, Text-to-Speech | **Kept** as "Voice tools", localized |
| `page_history.py`, `page_account.py`, `page_dashboard.py` | History, profile/settings, dashboard | **Rewritten/extended** for farmers |
| `llm_client.py` | OpenAI-compatible chat client | **Kept** as the `openai_compatible` provider transport |
| `assistant.py`, `agent_service.py` | Floating "how to use this app" help bot | **Removed** – it answered questions about the app UI, not farming, and its built-in answers were English-only and described removed pages. Superseded by *Ask AgriVoice* and a localized Help page |
| `assets/gnani_background.jpeg` | Blue voice-tech background | **Removed** – clashed with the green agricultural theme |

## Security finding (act on this)
The original `.env.example` (public GitHub repo, commit `d328963`) contained what looks like a **real Gnani API key**.
It is removed from the working tree in this upgrade, but **it remains in git history. Revoke/rotate that key in the Gnani console now.**
Optionally rewrite history (`git filter-repo --replace-text`) – rotation is what actually protects you.

## New architecture
```
Streamlit pages ──► ui.py (session, language selector, notices) ──► i18n.py (locales/*.json)
      │
      ├─ page_ask ─► stt_service ─► gnani_client (Prisma)
      │            ─► agri_service ─► llm_service (Claude | openai_compatible) ◄─ agri_prompts
      │            ─► tts_service ─► gnani_client (Timbre)
      ├─ page_crops / page_health / page_schemes ─► agri_service
      ├─ page_weather / dashboard ─► weather.py (Open-Meteo)
      └─ chat_store ─► database.py (SQLite)  |  session memory when "save history" is off
```

### Database v3 (migration preserves all existing rows; a backup is written first)
* `farmer_profiles(user_id UNIQUE, state, district, primary_crop, farm_size, latitude, longitude, place_name, updated_at)`
* `messages` + `language, input_mode (text/voice/upload), raw_transcript, feedback`
* `users` + `voice_reply`; `users.default_language` is now the farmer's single language preference (UI, answers, voice)
* Your spec's `conversations`/`messages` fields map to existing columns (`message_text` = `content`) – renaming was skipped to avoid breaking working data.

### Language model
One preference drives: interface (if `locales/<iso>.json` exists), the language Claude must answer in, the Prisma `language_code`, and the Timbre `language`.
Voice availability is separate from interface translation, so Odia/Assamese/Urdu can get text answers without pretending voice works.

## Gnani API facts used (docs.gnani.ai, checked 31 Oct 2026)
* STT REST: ≤ 30 s clips (the old code allowed 60 s – fixed). Prisma v3.0 is opt-in (`model=prisma-v3.0`, `language_code=indic-auto`).
* TTS: `POST https://api.vachana.ai/api/v1/tts/inference`, model `timbre-v2.5`. Existing, unchanged client.
* No Gnani LLM endpoint is documented → none used.

## Not done / deferred
Password reset (needs email), PostgreSQL implementation (documented path), translations beyond en/te/ta/hi, screenshots (no browser in the build environment).
