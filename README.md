# GNANI AGRI VOICE – Voice-Powered Agricultural Assistant

**Your Voice. Your Language. Your Farming Assistant.**

A multilingual voice assistant that helps Indian farmers get farming guidance in their own language.
A farmer speaks (or types) a question, checks the transcript, and receives an answer as text **and** speech.

```
Farmer speaks → Gnani Prisma STT → editable transcript → Claude (agricultural reasoning)
              → answer in the farmer's language → Gnani Timbre TTS → farmer listens
```

This project is an upgrade of **Gnani Voice Studio**. Authentication (email + Google), the database, the Prisma STT client and the
Timbre TTS client were kept and extended. See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for what changed and why.

## Features

| Area | What it does |
|---|---|
| **Ask AgriVoice** | Speak live, upload a recording, or type. Transcript is shown and editable before sending. Remembers the conversation, replay/pause audio, copy, "answer again", 👍/👎, new/delete conversation. |
| **Crop Advice** | Crop, stage, state, district, soil, water source, symptoms, and topic (general / irrigation / fertilizer / pest / season) → practical advice. Prefilled from the farmer's profile. |
| **Plant Health** | Describe (typed or spoken) and/or upload a photo → *possible* causes, signs to check, safe next steps, prevention, when to call an expert. Always labelled **not a confirmed diagnosis**. |
| **Weather** | Real data from Open-Meteo for the saved location (or any searched place): temperature, humidity, wind, rain and a 3-day outlook, plus precautions derived from those numbers. |
| **Government Schemes** | PM-KISAN, PMFBY, Soil Health Card, KCC, e-NAM with eligibility, benefits, documents, official link, and the **date last verified** (or a clear "not yet checked"). Optional AI explanation in the farmer's language, restricted to the listed facts. |
| **History & Profile** | Conversations, transcripts and speech files, visible and deletable only by their owner. Farm profile: state, district, main crop, farm size. |
| **Voice tools** | The original Speak Live, Record/Upload and Text-to-Speech pages, kept and localized. |

## Languages

The whole interface, the answers and the voice follow the language the farmer chooses. It is saved in their profile and restored at login.
Changing language never deletes history.

| Language | Interface | Voice (Gnani STT + TTS) |
|---|---|---|
| Telugu, Tamil, Hindi, English | Translated | Yes |
| Kannada, Malayalam, Bengali, Marathi, Gujarati, Punjabi | English screens + native-language answers | Yes |
| Odia, Assamese, Urdu | English screens + native-language **text** answers | **No** – not offered by Gnani's speech APIs; shown as "voice not available" |

Voice availability comes from Gnani's documented language list (docs.gnani.ai) and is defined once in `languages.py`.
Interface translations live in `locales/*.json` – see *Adding a language* below. **The Telugu, Tamil and Hindi texts should be reviewed by
native speakers before a public launch.**

## Setup

```bash
git clone https://github.com/bhavanasisaiganesh77-hash/Gnani-Voice-Studio
cd Gnani-Voice-Studio
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                  # then fill in your keys
streamlit run streamlit_app.py
```

### Keys (never commit them)

| Variable | Purpose |
|---|---|
| `GNANI_API_KEY` | Gnani Prisma STT and Timbre TTS (same key) |
| `ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL` | Claude, for agricultural reasoning |
| `LLM_PROVIDER` | `anthropic` (default) or `openai_compatible` |
| `AI_REPLIES_PER_HOUR` | Per-user limit on AI answers (default 40) |

Local: `.env` or `.streamlit/secrets.toml` (both are git-ignored). Deployed: Streamlit *Secrets*. Without a Gnani key the app still runs; voice features show "service unavailable".
Without an LLM key the assistant says it is unavailable; nothing is faked.

> **Claude is not a Gnani model.** Gnani provides speech (Prisma STT, Timbre TTS). Reasoning is done by a separate, replaceable service (`llm_service.py`).
> No Gnani LLM endpoint is publicly documented, so none is used.

## Using it – demo workflow

See [docs/DEMO_WORKFLOW.md](docs/DEMO_WORKFLOW.md) for a step-by-step walkthrough and sample questions in Telugu, Tamil and Hindi.

## Project structure

```
streamlit_app.py      entrypoint + navigation          i18n.py / locales/*.json   localization
page_*.py             one file per page                llm_service.py             replaceable LLM providers (Claude)
agri_prompts.py       all prompts + safety rules       agri_service.py            rate limit → prompt → provider
stt_service.py        Prisma wrapper (+ auto-detect)   tts_service.py             Timbre wrapper (chunking, WAV join)
gnani_client.py       Gnani REST client (original)     weather.py                 Open-Meteo
schemes.py + data/    scheme facts + verification      database.py                SQLite, versioned migrations
chat_store.py         DB or session-only chats         tests/                     pytest suite
```

## Safety design

* The system prompt forbids unsupported pesticide/fertilizer doses, chemical mixtures, invented schemes/prices/weather, and requires uncertainty and KVK referral.
* Plant-health output is always framed as *possible* causes; confidence is capped at "medium".
* Weather is only ever real Open-Meteo data; if unreachable the app says so.
* Scheme facts come from `data/schemes.json`; entries not yet checked show no figures and a warning.
* Security: password hashing, per-user data isolation on every query, upload type/size/duration limits, image re-encoding (strips GPS metadata),
  HTML-escaping of all AI text, API timeouts, per-user rate limiting, logs without keys or user text.

## Adding a language interface

1. Copy `locales/en.json` to `locales/<iso>.json` (e.g. `kn.json`) and translate the values (keep `{placeholders}`; translate the `"msg"` block too).
2. Make sure the language's iso code is in `languages.ISO`.
3. Run `pytest` – it fails if any key or placeholder is missing.

## Updating government schemes

Edit `data/schemes.json` from the official website and set `last_verified` to that day. Leave it `null` for anything unchecked.

## Tests

```bash
pytest -q        # 124 tests: localization, database, providers, weather, speech services, full pages in 5 languages
```
External services (Claude, Gnani, Open-Meteo) are mocked in tests. **Live calls to Gnani, Claude and Open-Meteo have not been run by the author of this upgrade** – see *Known limitations*.

## Known limitations

* **Not verified live:** Gnani STT/TTS, Claude and Open-Meteo calls were tested against mocks and the documented request formats, not with real keys. Run the demo workflow once with your keys.
* **Password reset** is not implemented (it needs an email service).
* **SQLite on Streamlit Community Cloud is not durable** – the disk is reset on restart. Use it for demos; for real users move to PostgreSQL (see docs/DEPLOYMENT.md).
* Prisma v3.0 language auto-detect is opt-in per Gnani's docs and has not been confirmed enabled on your account; the app falls back to the selected language automatically.
* Interface translations exist for English, Telugu, Tamil and Hindi only.
* Government-scheme details were checked on 30 Oct 2026 for PM-KISAN and PMFBY only.
* The assistant gives guidance, not expert advice. Voice answers longer than ~3,200 characters are shortened for audio (the full text is always shown).
