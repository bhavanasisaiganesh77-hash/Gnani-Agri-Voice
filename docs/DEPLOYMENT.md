# Deployment – Streamlit Community Cloud

1. Push the `agri-voice-upgrade` branch (or merge it into `main`) on GitHub. **Do not commit `.env` or `secrets.toml`.**
2. **Rotate the Gnani key first** – the previous `.env.example` contained a real key (see ARCHITECTURE.md, "Security finding").
3. share.streamlit.io → *New app* → pick the repo, branch, main file `streamlit_app.py`. Python 3.11+.
4. *Advanced settings → Secrets*: paste the contents of `.streamlit/secrets.toml.example` with your real values.
5. Google sign-in (optional): in Google Cloud add `https://<your-app>.streamlit.app/oauth2callback` as an authorized redirect URI and set the same value as `redirect_uri` in secrets.
6. Deploy, then run the demo workflow once.

## Important: database persistence
The app uses SQLite (`agri_voice.db`, path via `VOICE_STUDIO_DB`). **Streamlit Community Cloud's disk is ephemeral**: accounts and history are lost whenever the app restarts or is redeployed.
That is fine for a demo. For real farmers, move `database.py` to a managed PostgreSQL (e.g. Neon or Supabase free tiers). The data layer is confined to
`database.py`, with plain SQL and a single connection helper; the migration blocks in `init_db()` document the schema.

## Operations
* Cost control: `AI_REPLIES_PER_HOUR` limits Claude calls per user (in memory, per process).
* Microphone recording needs HTTPS (Community Cloud provides it).
* Logs contain status codes only – never keys or farmer text.
