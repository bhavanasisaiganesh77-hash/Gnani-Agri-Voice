"""Glassmorphism design system for GNANI AGRI VOICE.

HOW THE STYLING IS ATTACHED (so it does not depend on Streamlit's internal HTML):
  * Cards      : st.container(key="card_...")  ->  Streamlit adds the class  st-key-card_...
  * Buttons    : st.button(key="gp_...")       ->  st-key-gp_...   (primary glass, orange)
                 st.button(key="gs_...")       ->  st-key-gs_...   (stop / danger glass, red)
                 st.button(key="gg_...")       ->  st-key-gg_...   (ghost glass, white)
  The CSS below targets those key classes, so you restyle a button just by changing its key prefix.
  The floating assistant uses the containers  assist_fab  and  assist_panel  (see assistant.py).
"""

import urllib.parse
import streamlit as st

_G = ("<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 48 48'>"
      "<path fill='#EA4335' d='M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z'/>"
      "<path fill='#4285F4' d='M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z'/>"
      "<path fill='#FBBC05' d='M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z'/>"
      "<path fill='#34A853' d='M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z'/></svg>")
GOOGLE_ICON_URI = "data:image/svg+xml;utf8," + urllib.parse.quote(_G)

BASE_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,600;12..96,700&family=Figtree:wght@400;500;600&family=Noto+Sans+Telugu:wght@400;500;700&family=Noto+Sans+Tamil:wght@400;500;700&family=Noto+Sans+Devanagari:wght@400;500;700&family=Noto+Sans+Kannada:wght@400;500;700&family=Noto+Sans+Malayalam:wght@400;500;700&family=Noto+Sans+Bengali:wght@400;500;700&family=Noto+Sans+Gujarati:wght@400;500;700&family=Noto+Sans+Gurmukhi:wght@400;500;700&family=Noto+Sans+Oriya:wght@400;500;700&family=Noto+Naskh+Arabic:wght@400;500;700&display=swap');

:root{
  --navy:#10261A; --muted:#4B5F52; --green:#2E7D32; --green-deep:#1B5E20; --green-soft:#E3F4E4;
  --glass:rgba(255,255,255,.94); --glass-line:rgba(255,255,255,.78); --line:rgba(46,125,50,.16);
  --ok:#1F6B42; --warn:#7A4A00; --err:#9B1C14;
}
.stApp, .stApp button, .stApp textarea, .stApp input{font-family:'Figtree','Noto Sans Telugu','Noto Sans Tamil','Noto Sans Devanagari','Noto Sans Kannada','Noto Sans Malayalam','Noto Sans Bengali','Noto Sans Gujarati','Noto Sans Gurmukhi','Noto Sans Oriya','Noto Naskh Arabic',system-ui,sans-serif;}
.stApp{
  color:var(--navy); background-color:#F4FAF2;
  background-image:
    radial-gradient(900px 520px at 6% -6%, rgba(120,200,120,.22), transparent 62%),
    radial-gradient(760px 520px at 100% 0%, rgba(200,232,180,.32), transparent 58%),
    radial-gradient(900px 620px at 50% 112%, rgba(80,170,90,.12), transparent 62%);
  background-attachment:fixed;
}
#MainMenu, footer{visibility:hidden;}
header[data-testid="stHeader"]{background:transparent;}
html, body, .stApp{overflow-x:hidden;}
.block-container{max-width:1120px;padding:2rem 1.5rem 7rem;}
h1,h2,h3{color:var(--navy);}

/* ---------- Sidebar ---------- */
section[data-testid="stSidebar"]{background:rgba(236,247,234,.86);border-right:1px solid var(--line);
  -webkit-backdrop-filter:blur(14px);backdrop-filter:blur(14px);}
.user-card{display:flex;align-items:center;gap:.7rem;background:var(--glass);border:1px solid var(--glass-line);
  border-radius:16px;padding:.7rem .8rem;margin:1rem 0 .6rem;box-shadow:0 10px 24px -18px rgba(27,94,32,.45);}
.avatar{flex:none;width:38px;height:38px;border-radius:50%;display:grid;place-items:center;font-weight:700;color:#fff;
  background:linear-gradient(135deg,#2E7D32,#14471A);}
.avatar.big{width:68px;height:68px;font-size:1.7rem;}
.user-card .who{min-width:0;}
.user-card b{display:block;font-size:.95rem;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}
.user-card small{color:var(--muted);display:block;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}

/* ---------- Headings ---------- */
.page-head{display:flex;align-items:center;gap:.8rem;margin:0 0 1.4rem;}
.page-title{font-family:'Bricolage Grotesque',sans-serif;font-weight:700;font-size:1.9rem;letter-spacing:-.02em;margin:0;padding:0;color:var(--navy);}
.brand-mark{width:48px;height:48px;border-radius:14px;display:grid;place-items:center;
  background:linear-gradient(135deg,#4CAF50,#1B5E20);box-shadow:0 10px 22px -10px rgba(27,94,32,.8);}
.chip{flex:none;width:42px;height:42px;border-radius:13px;display:grid;place-items:center;color:var(--green-deep);
  background:linear-gradient(135deg,rgba(255,255,255,.9),var(--green-soft));border:1px solid var(--line);}

/* ---------- Glass cards ---------- */
[class*="st-key-card_"], .st-key-band{
  background:var(--glass);border:1px solid var(--glass-line);border-radius:22px;padding:1.5rem;
  -webkit-backdrop-filter:blur(18px) saturate(150%);backdrop-filter:blur(18px) saturate(150%);
  box-shadow:0 0 0 1px var(--line), 0 18px 40px -24px rgba(27,94,32,.42), inset 0 1px 0 rgba(255,255,255,.9);}
.st-key-band{padding:1.4rem;margin-bottom:1.4rem;background:rgba(245,252,244,.96);}
@supports not ((backdrop-filter:blur(1px)) or (-webkit-backdrop-filter:blur(1px))){
  [class*="st-key-card_"], .st-key-band{background:rgba(255,255,255,.95);}
}
.card-head{display:flex;gap:.8rem;align-items:center;margin-bottom:.9rem;}
.card-head h3{font-family:'Bricolage Grotesque',sans-serif;font-weight:600;font-size:1.2rem;margin:0;padding:0;}

/* ---------- Glass buttons (see key prefixes in the module docstring) ---------- */
[class*="st-key-gp_"], [class*="st-key-gs_"], [class*="st-key-gg_"]{width:100%;}
[class*="st-key-gp_"] button, [class*="st-key-gs_"] button, [class*="st-key-gg_"] button{
  width:100%;min-height:46px;border-radius:14px;font-weight:600;font-size:.98rem;cursor:pointer;
  -webkit-backdrop-filter:blur(12px) saturate(160%);backdrop-filter:blur(12px) saturate(160%);
  transition:transform .18s ease, box-shadow .18s ease, background .18s ease, border-color .18s ease, filter .18s ease;}
[class*="st-key-gp_"] button *, [class*="st-key-gs_"] button *, [class*="st-key-gg_"] button *{color:inherit !important;}
[class*="st-key-gp_"] button{
  color:#fff !important;border:1px solid rgba(255,255,255,.5) !important;
  background:linear-gradient(135deg, rgba(27,94,32,.96), rgba(20,71,26,.97)) !important;
  box-shadow:0 12px 26px -12px rgba(20,71,26,.75), inset 0 1px 0 rgba(255,255,255,.38);}
[class*="st-key-gp_"] button:hover:not(:disabled){transform:translateY(-1px);filter:brightness(1.07);
  box-shadow:0 16px 30px -12px rgba(20,71,26,.85), inset 0 1px 0 rgba(255,255,255,.45);}
[class*="st-key-gs_"] button{
  color:var(--err) !important;border:1px solid rgba(155,28,20,.38) !important;background:rgba(255,236,233,.72) !important;
  box-shadow:0 10px 22px -16px rgba(155,28,20,.6), inset 0 1px 0 rgba(255,255,255,.8);}
[class*="st-key-gs_"] button:hover:not(:disabled){transform:translateY(-1px);background:rgba(255,226,222,.92) !important;border-color:rgba(155,28,20,.6) !important;}
[class*="st-key-gg_"] button{
  color:var(--green-deep) !important;border:1px solid rgba(46,125,50,.30) !important;background:rgba(255,255,255,.62) !important;
  box-shadow:0 10px 22px -16px rgba(27,94,32,.5), inset 0 1px 0 rgba(255,255,255,.9);}
[class*="st-key-gg_"] button:hover:not(:disabled){transform:translateY(-1px);background:rgba(255,255,255,.9) !important;border-color:rgba(46,125,50,.6) !important;}
[class*="st-key-gp_"] button:active:not(:disabled), [class*="st-key-gs_"] button:active:not(:disabled),
[class*="st-key-gg_"] button:active:not(:disabled){transform:translateY(0) scale(.985);}
[class*="st-key-gp_"] button:disabled, [class*="st-key-gs_"] button:disabled, [class*="st-key-gg_"] button:disabled{
  opacity:.5;cursor:not-allowed;box-shadow:none;}
button:focus-visible, a:focus-visible, textarea:focus-visible, input:focus-visible{outline:3px solid #81C784 !important;outline-offset:2px;}

/* Continue with Google: the real multicolour Google "G" */
.st-key-gg_google button{gap:.7rem;color:var(--navy) !important;}
.st-key-gg_google button::before{content:"";width:20px;height:20px;flex:none;background:url("__GOOGLE__") center/contain no-repeat;}

/* Quick-access cards: title on its own line, links side by side */
[class*="st-key-card_quick"]{flex-direction:row;flex-wrap:wrap;align-items:center;gap:.6rem;}
[class*="st-key-card_quick"] > div{width:auto;}
[class*="st-key-card_quick"] > div:first-child{flex:0 0 100%;}
/* Quick-access link buttons */
[class*="st-key-card_quick"] a{display:flex;justify-content:center;align-items:center;min-height:44px;border-radius:14px;font-weight:600;
  color:var(--green-deep) !important;text-decoration:none;background:rgba(255,255,255,.62);border:1px solid rgba(46,125,50,.30);
  transition:transform .18s ease, background .18s ease;}
[class*="st-key-card_quick"] a:hover{transform:translateY(-1px);background:rgba(255,255,255,.92);}
[class*="st-key-card_quick"] a *{color:inherit !important;}

/* ---------- Inputs ---------- */
.stTextInput input, .stTextArea textarea, .stSelectbox div[data-baseweb="select"] > div{border-radius:12px;}
.stTextInput input:focus, .stTextArea textarea:focus{border-color:var(--green) !important;box-shadow:0 0 0 3px rgba(46,125,50,.2) !important;}
[class*="st-key-card_"] textarea{font-family:'Figtree','Noto Sans Telugu','Noto Sans Tamil','Noto Sans Devanagari','Noto Sans Kannada','Noto Sans Malayalam','Noto Sans Bengali','Noto Sans Gujarati','Noto Sans Gurmukhi','Noto Sans Oriya','Noto Naskh Arabic',sans-serif !important;font-size:1.1rem;line-height:1.85;background:rgba(250,254,249,.95);}

/* ---------- Pills, notices, loading ---------- */
.pill{display:inline-flex;align-items:center;gap:.5rem;font-size:.88rem;font-weight:500;padding:.3rem .8rem;border-radius:999px;
  background:rgba(255,255,255,.7);color:var(--muted);border:1px solid var(--line);margin:.2rem 0 .8rem;}
.pill::before{content:"";width:8px;height:8px;border-radius:50%;background:#A9BFA9;}
.pill.ready{background:var(--green-soft);color:var(--green-deep);border-color:#BFE3C2;} .pill.ready::before{background:var(--green);}
.pill.done{background:#E7F5EC;color:var(--ok);border-color:#BFE1CC;} .pill.done::before{background:var(--ok);}
.pill.warn{background:#FFF4D6;color:var(--warn);border-color:#F2DC9B;} .pill.warn::before{background:#D49A00;}
.pill.busy::before{background:var(--green);animation:blink 1s ease-in-out infinite;}
@keyframes blink{50%{opacity:.25}}
.notice{border-radius:16px;padding:1rem 1.2rem;margin:.4rem 0 1.2rem;border:1px solid;
  -webkit-backdrop-filter:blur(10px);backdrop-filter:blur(10px);}
.notice b{display:block;margin-bottom:.15rem;}
.notice.error{background:rgba(255,238,235,.85);border-color:#F1C4BE;color:#6E140E;}
.notice.warn{background:rgba(255,247,222,.9);border-color:#F2DC9B;color:#5E3A00;}
.notice.info{background:rgba(236,247,234,.92);border-color:var(--line);color:var(--navy);}
.notice.ok{background:rgba(232,246,237,.9);border-color:#BFE1CC;color:#164F30;}
.loading{display:flex;align-items:center;gap:1rem;background:var(--glass);border:1px solid var(--glass-line);border-radius:18px;
  padding:1rem 1.25rem;margin:.4rem 0 1.4rem;box-shadow:0 0 0 1px var(--line), 0 14px 30px -22px rgba(27,94,32,.55);}
.bars{display:flex;align-items:center;gap:4px;height:32px;}
.bars span{width:5px;height:100%;border-radius:3px;background:linear-gradient(180deg,#4CAF50,#14471A);animation:wave 1s ease-in-out infinite;}
.bars span:nth-child(2){animation-delay:.12s}.bars span:nth-child(3){animation-delay:.24s}
.bars span:nth-child(4){animation-delay:.36s}.bars span:nth-child(5){animation-delay:.48s}
@keyframes wave{0%,100%{transform:scaleY(.25)}50%{transform:scaleY(1)}}
.loading b{display:block;font-weight:600;}

/* Record and Upload cards: equal height, Transcribe buttons aligned on the bottom edge */
.st-key-card_ru_record, .st-key-card_ru_upload{min-height:272px;}
.st-key-card_ru_record > div:last-child, .st-key-card_ru_upload > div:last-child{margin-top:auto;}

/* ---------- Text areas, chat bubbles ---------- */
.hint{color:var(--muted);font-size:.85rem;margin:.4rem 0 .9rem;}
.hint.count{text-align:right;margin:.2rem 0 .8rem;}
.bubble{max-width:86%;padding:.6rem .85rem;border-radius:16px;line-height:1.5;font-size:.93rem;white-space:pre-wrap;word-wrap:break-word;
  font-family:'Figtree','Noto Sans Telugu','Noto Sans Tamil','Noto Sans Devanagari','Noto Sans Kannada','Noto Sans Malayalam','Noto Sans Bengali','Noto Sans Gujarati','Noto Sans Gurmukhi','Noto Sans Oriya','Noto Naskh Arabic',sans-serif;box-shadow:0 8px 20px -16px rgba(16,38,26,.5);}
.bubble.user{align-self:flex-end;color:#fff;background:linear-gradient(135deg, rgba(27,94,32,.96), rgba(20,71,26,.97));border-bottom-right-radius:5px;}
.bubble.assistant{align-self:flex-start;color:var(--navy);background:rgba(236,247,235,.96);border:1px solid var(--line);border-bottom-left-radius:5px;}
.bubble.typing{display:flex;gap:5px;padding:.75rem .9rem;}
.bubble.typing i{width:7px;height:7px;border-radius:50%;background:#A9BFA9;animation:blink 1s ease-in-out infinite;}
.bubble.typing i:nth-child(2){animation-delay:.15s}.bubble.typing i:nth-child(3){animation-delay:.3s}
.chat{display:flex;flex-direction:column;gap:.6rem;margin:.4rem 0;}
.empty{color:var(--muted);text-align:center;padding:1.4rem 1rem;}
.user-card.plain{border:0;padding:0;margin:0 0 1rem;background:none;box-shadow:none;}
.user-card b.big{font-size:1.25rem;}

/* ---------- Floating assistant ---------- */
.st-key-assist_fab{position:fixed;right:24px;bottom:24px;z-index:1000;width:56px !important;}
.st-key-assist_fab [class*="st-key-gp_"]{width:56px;}
.st-key-assist_fab [class*="st-key-gp_"] button{width:56px;height:56px;min-height:56px;padding:0;border-radius:50%;
  box-shadow:0 16px 32px -10px rgba(20,71,26,.75), inset 0 1px 0 rgba(255,255,255,.4);}
.st-key-assist_fab button p{font-size:0;line-height:0;margin:0;}  /* label stays for screen readers, icon is what people see */
.st-key-assist_panel{position:fixed;right:24px;bottom:92px;z-index:1000;box-sizing:border-box;
  width:min(380px, calc(100vw - 32px));max-height:min(580px, calc(100dvh - 120px));overflow-y:auto;overflow-x:hidden;
  background:rgba(255,255,255,.9);border:1px solid var(--glass-line);border-radius:22px;padding:1rem;
  -webkit-backdrop-filter:blur(20px) saturate(150%);backdrop-filter:blur(20px) saturate(150%);
  box-shadow:0 0 0 1px var(--line), 0 28px 60px -20px rgba(16,38,26,.45);animation:assist-in .2s ease-out;}
@keyframes assist-in{from{opacity:0;transform:translateY(12px) scale(.98)}to{opacity:1;transform:none}}
.assist-title{font-family:'Bricolage Grotesque',sans-serif;font-weight:700;font-size:1.1rem;}
.assist-scroll{display:flex;flex-direction:column-reverse;gap:.5rem;max-height:min(300px, 36vh);overflow-y:auto;padding:.1rem .1rem .3rem;}
.st-key-assist_chips{flex-direction:row !important;flex-wrap:wrap;gap:.4rem !important;}
.st-key-assist_chips > div{width:auto !important;flex:0 0 auto;}
.st-key-assist_chips [class*="st-key-gg_"]{width:auto;}
.st-key-assist_chips [class*="st-key-gg_"] button{width:auto;min-height:34px;padding:.2rem .8rem;border-radius:999px;font-size:.85rem;}
.st-key-assist_panel [class*="st-key-gg_assist_clear"] button{min-height:34px;font-size:.85rem;}
/* keep the title and Clear on one line, even on phones (Streamlit stacks columns there) */
.st-key-assist_panel [data-testid="stHorizontalBlock"]{flex-direction:row !important;flex-wrap:nowrap !important;align-items:center;gap:.5rem;}
.st-key-assist_panel [data-testid="stColumn"]{min-width:0 !important;width:auto !important;flex:1 1 auto !important;}
.st-key-assist_panel [data-testid="stColumn"]:last-child{flex:0 0 auto !important;}
/* message box and send button on one row */
.st-key-assist_panel [data-testid="stForm"]{border:0;padding:0;}
.st-key-assist_panel [data-testid="stForm"] > div{flex-direction:row;align-items:flex-start;gap:.5rem;}
.st-key-assist_input{flex:1 1 auto;min-width:0;}
.st-key-assist_panel .st-key-gp_assist_send{flex:0 0 auto;width:46px;}
.st-key-assist_panel .st-key-gp_assist_send button{width:46px;min-width:46px;padding:0;border-radius:14px;}
.st-key-assist_panel .st-key-gp_assist_send button p{font-size:0;line-height:0;margin:0;}
[data-testid="InputInstructions"]{display:none;}

/* ---------- Dashboard ---------- */
.stats{display:grid;grid-template-columns:repeat(2,1fr);gap:.9rem;margin:1.2rem 0;}
.stat{background:var(--glass);border:1px solid var(--glass-line);border-radius:18px;padding:1rem 1.1rem;
  box-shadow:0 0 0 1px var(--line), 0 14px 30px -24px rgba(27,94,32,.5);-webkit-backdrop-filter:blur(14px);backdrop-filter:blur(14px);}
.stat b{display:block;font-family:'Bricolage Grotesque',sans-serif;font-size:1.9rem;line-height:1.1;color:var(--navy);}
.stat span{color:var(--muted);font-size:.9rem;}
.activity{display:flex;gap:.8rem;align-items:flex-start;padding:.7rem 0;border-bottom:1px solid var(--line);}
.activity:last-child{border-bottom:0;}
.activity .dot{flex:none;width:10px;height:10px;border-radius:50%;background:var(--green);margin-top:.5rem;}
.activity b{display:block;} .activity small{color:var(--muted);}
.fine{color:var(--muted);font-size:.85rem;margin-top:1.6rem;text-align:center;}

@media (max-width:640px){
  .block-container{padding:1.1rem .9rem 6.5rem;} .page-title{font-size:1.6rem;}
  [class*="st-key-card_"], .st-key-band{padding:1.05rem;border-radius:20px;}
  .bubble{max-width:92%;}
  .st-key-assist_fab{right:16px;bottom:16px;}
  .st-key-assist_panel{right:12px;left:12px;width:auto;bottom:84px;max-height:calc(100dvh - 110px);}
}
@media (prefers-reduced-motion:reduce){
  .bars span, .pill.busy::before, .bubble.typing i, .st-key-assist_panel{animation:none;}
  [class*="st-key-gp_"] button, [class*="st-key-gs_"] button, [class*="st-key-gg_"] button{transition:none;}
}
/* ---------- Improved readability ---------- */

/* Main content text */
.stApp [data-testid="stMain"] {
    color: #183323 !important;
}

.stApp [data-testid="stMarkdownContainer"],
.stApp [data-testid="stMarkdownContainer"] p,
.stApp [data-testid="stMarkdownContainer"] li,
.stApp label,
.stApp .stCaption {
    color: #183323 !important;
}

/* Streamlit warning, error and information messages */
.stApp [data-testid="stAlert"] {
    opacity: 1 !important;
    border-radius: 14px !important;
    border: 1px solid #D5B86A !important;
    background: #FFF9E8 !important;
    color: #493500 !important;
    box-shadow: 0 5px 18px rgba(0,0,0,.08);
}

.stApp [data-testid="stAlert"] p,
.stApp [data-testid="stAlert"] div,
.stApp [data-testid="stAlert"] span {
    color: #493500 !important;
}

/* Input text */
.stApp textarea,
.stApp input {
    color: #183323 !important;
    background: #FFFFFF !important;
}

.stApp textarea::placeholder,
.stApp input::placeholder {
    color: #647568 !important;
    opacity: 1 !important;
}

/* Stronger glass panels */
[class*="st-key-card_"],
.st-key-band {
    background: rgba(255,255,255,.94) !important;
    color: #183323 !important;
    -webkit-backdrop-filter: blur(18px);
    backdrop-filter: blur(18px);
}
/* ---------- Button text visibility fix ---------- */

/* Main green buttons */
.stApp [class*="st-key-gp_"] button,
.stApp [class*="st-key-gp_"] button p,
.stApp [class*="st-key-gp_"] button span {
    color: #FFFFFF !important;
    -webkit-text-fill-color: #FFFFFF !important;
}

/* Secondary green-text buttons */
.stApp [class*="st-key-gg_"] button,
.stApp [class*="st-key-gg_"] button p,
.stApp [class*="st-key-gg_"] button span {
    color: #1B5E20 !important;
    -webkit-text-fill-color: #1B5E20 !important;
}

/* Red/destructive buttons */
.stApp [class*="st-key-gs_"] button,
.stApp [class*="st-key-gs_"] button p,
.stApp [class*="st-key-gs_"] button span {
    color: #9B1C14 !important;
    -webkit-text-fill-color: #9B1C14 !important;
}
/* Login and signup button text visibility */
.stApp [class*="st-key-"] button[kind="primary"],
.stApp [class*="st-key-"] button[kind="primary"] p,
.stApp [class*="st-key-"] button[kind="primary"] span {
    color: #FFFFFF !important;
    -webkit-text-fill-color: #FFFFFF !important;
    font-weight: 700 !important;
}

/* Green buttons */
.stApp button[kind="primary"] {
    background-color: #2E7D32 !important;
    border: 1px solid #1B5E20 !important;
}
</style>
""".replace("__GOOGLE__", GOOGLE_ICON_URI)

# Signed-out pages: no sidebar, split brand/form layout.
AUTH_CSS = """
<style>
section[data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"], [data-testid="collapsedControl"]{display:none !important;}
.block-container{max-width:1000px;padding-top:3rem;}
.st-key-auth_brand{background:linear-gradient(150deg,#2E7D32 0%,#14471A 100%);color:#fff;border-radius:28px;padding:2.2rem;min-height:100%;
  box-shadow:0 30px 50px -30px rgba(20,71,26,.9), inset 0 1px 0 rgba(255,255,255,.3);}
.st-key-auth_brand h2{font-family:'Bricolage Grotesque',sans-serif;font-weight:700;font-size:2rem;line-height:1.15;letter-spacing:-.02em;color:#fff;margin:1.2rem 0 .8rem;padding:0;}
.st-key-auth_brand p, .st-key-auth_brand li{color:#E8F5E9;font-size:1rem;}
.st-key-auth_brand ul{padding-left:1.1rem;margin:1rem 0 0;} .st-key-auth_brand li{margin:.45rem 0;}
.st-key-auth_brand .brand-mark{background:rgba(255,255,255,.2);box-shadow:inset 0 1px 0 rgba(255,255,255,.4);}
.auth-title{font-family:'Bricolage Grotesque',sans-serif;font-weight:700;font-size:1.7rem;margin:0 0 .2rem;padding:0;}
.auth-sub{color:var(--muted);margin:0 0 1rem;}
.or-line{display:flex;align-items:center;gap:.8rem;color:var(--muted);font-size:.9rem;margin:1rem 0;}
.or-line::before, .or-line::after{content:"";flex:1;height:1px;background:var(--line);}
/* ===== LOGIN PAGE: WELCOME PANEL TEXT FIX ===== */

.stApp [class*="st-key-"] {
    --auth-text: #183323;
}

/* Welcome panel heading */
.stApp .auth-hero h1,
.stApp .auth-hero h2,
.stApp .auth-hero h3 {
    color: #FFFFFF !important;
    -webkit-text-fill-color: #FFFFFF !important;
    font-weight: 800 !important;
}

/* Welcome panel description and tagline */
.stApp .auth-hero p,
.stApp .auth-hero span,
.stApp .auth-hero div {
    color: #F1FFF2 !important;
    -webkit-text-fill-color: #F1FFF2 !important;
}

/* Login button */
.stApp button[kind="primary"],
.stApp button[kind="primary"] p,
.stApp button[kind="primary"] span {
    color: #FFFFFF !important;
    -webkit-text-fill-color: #FFFFFF !important;
    font-weight: 700 !important;
}

/* Login form labels */
.stApp label,
.stApp label p {
    color: #183323 !important;
    -webkit-text-fill-color: #183323 !important;
}
</style>
"""


import base64
import streamlit as st
from pathlib import Path


def set_agri_background():
    import base64
    from pathlib import Path
    import streamlit as st

    image_path = Path(__file__).parent / "assets" / "agri-background.jpeg"

    if not image_path.is_file():
        st.warning("Agricultural background image not found.")
        return

    image_data = base64.b64encode(
        image_path.read_bytes()
    ).decode("utf-8")

    st.markdown(
        f"""
        <style>

        /* Agricultural background */
        .stApp {{
            background-image:
                linear-gradient(
                    rgba(10, 35, 15, 0.20),
                    rgba(10, 35, 15, 0.20)
                ),
                url("data:image/jpeg;base64,{image_data}") !important;

            background-size: cover !important;
            background-position: center !important;
            background-attachment: fixed !important;
        }}

        /* Transparent main application layer */
        [data-testid="stAppViewContainer"],
        [data-testid="stMain"] {{
            background: transparent !important;
        }}

        /* Glass content container */
        [data-testid="stMainBlockContainer"] {{
            background: rgba(255, 255, 255, 0.88) !important;
            backdrop-filter: blur(18px);
            -webkit-backdrop-filter: blur(18px);
            border: 1px solid rgba(255, 255, 255, 0.65);
            border-radius: 22px;
            padding: 2rem !important;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.12);
        }}

        /* Text clarity */
        [data-testid="stMainBlockContainer"] p,
        [data-testid="stMainBlockContainer"] label,
        [data-testid="stMainBlockContainer"] h1,
        [data-testid="stMainBlockContainer"] h2,
        [data-testid="stMainBlockContainer"] h3,
        [data-testid="stMainBlockContainer"] span {{
            color: #183b25;
        }}

        /* Sidebar glass effect */
        [data-testid="stSidebar"] {{
            background: rgba(245, 250, 243, 0.96) !important;
            backdrop-filter: blur(15px);
        }}

        /* Buttons */
        .stButton > button {{
            background-color: #247a3c;
            color: white !important;
            border: none;
            border-radius: 10px;
            font-weight: 600;
        }}

        .stButton > button:hover {{
            background-color: #185b2b;
            color: white !important;
        }}

        /* Mobile */
        @media (max-width: 768px) {{
            [data-testid="stMainBlockContainer"] {{
                padding: 1rem !important;
                border-radius: 14px;
            }}

            .stApp {{
                background-attachment: scroll !important;
            }}
        }}

        </style>
        """,
        unsafe_allow_html=True
    )