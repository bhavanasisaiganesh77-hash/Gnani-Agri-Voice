# Demo workflow

Prerequisites: `GNANI_API_KEY` and `ANTHROPIC_API_KEY` set, `streamlit run streamlit_app.py`.

## 1. Sign up in Telugu
1. On the sign-up screen choose **తెలుగు** in the language box – the whole screen switches.
2. Create the account. Log in. The Home screen is in Telugu (language restored from your profile).

## 2. Set up the farm
**నా పొలం & ప్రొఫైల్** → state *Andhra Pradesh*, district *Guntur*, crop *వరి* → Save.
The weather location is resolved through Open-Meteo; Home now shows real weather.

## 3. Ask by voice
**AgriVoiceని అడగండి** → 🎤 press the microphone and say:

| Language | Question |
|---|---|
| Telugu | నా వరి పంట ఆకులు పసుపు రంగులోకి మారుతున్నాయి. ఏం చేయాలి? |
| Tamil | என் நெற்பயிரின் இலைகள் மஞ்சள் நிறமாக மாறுகின்றன. என்ன செய்ய வேண்டும்? |
| Hindi | मेरी धान की फसल की पत्तियाँ पीली हो रही हैं। मुझे क्या करना चाहिए? |

Check the transcript, fix any mistakes, press **Send**. You get the answer in text and spoken aloud (replay with the player).
Ask a follow-up ("what about fertilizer?") – the assistant remembers the conversation.

## 4. Switch language mid-way
Change the language in the sidebar to **தமிழ்** – screens and the next answer switch to Tamil; your earlier conversation is still in **History**.

## 5. Other features
* **Plant Health:** describe symptoms (or upload a leaf photo) → possible causes, never a confirmed diagnosis.
* **Crop Advice → Irrigation:** pick cotton, flowering, canal water → advice.
* **Schemes:** PM-KISAN shows "Last checked: 2026-10-30"; e-NAM shows "not yet checked".
* **Odia / Assamese / Urdu:** voice controls are replaced by a "voice not available" note; typed questions still get text answers.

## What to expect to be checked manually
Real microphone capture, real Gnani transcription quality in each language, Timbre voice quality, and Claude's answers. These depend on your keys and cannot be verified offline.
