import json
import random
import re
import io
import html
import streamlit as st
import streamlit.components.v1 as components
import tempfile
from pathlib import Path
import speech_recognition as sr
from supabase import create_client, Client


# --- LIVE SPEECH RECOGNITION (No audio file saved) ---
@st.cache_resource
def _live_speech_component():
    component_dir = Path(tempfile.gettempdir()) / "pilotinterviewpro_live_speech_component"
    component_dir.mkdir(parents=True, exist_ok=True)
    html_path = component_dir / "index.html"
    html_path.write_text(r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
:root { color-scheme: light; background: transparent !important; }
* { box-sizing: border-box; }
html, body { margin:0 !important; padding:0 !important; width:100%; min-height:0 !important; background:rgba(7,23,43,0) !important; background-color:transparent !important; color:#EAF2FF; overflow:hidden; }
body { font-family:Arial,sans-serif; }
.wrap { display:flex; align-items:center; gap:14px; padding:5px 2px; min-height:72px; background:transparent !important; }
.mic { width:60px;height:60px;flex:0 0 60px;border-radius:50%;border:2px solid #83DFFF;
 background:radial-gradient(circle at 32% 24%,#63B8FF 0%,#287CE1 42%,#0B347B 100%);
 color:#fff;font-size:27px;cursor:pointer;box-shadow:0 0 0 6px rgba(53,189,245,.12),0 0 28px rgba(41,132,255,.38);
 transition:transform .18s,box-shadow .18s; }
.mic:hover { transform:scale(1.05);box-shadow:0 0 0 9px rgba(53,189,245,.15),0 0 38px rgba(41,132,255,.5); }
.mic.live { background:radial-gradient(circle at 32% 24%,#ff9a9a 0%,#d94358 48%,#711d39 100%);border-color:#ffb0ba; }
.texts { min-width:0; }
.title { font-size:14px;font-weight:700;margin-bottom:6px;color:#F3F7FF; }
.status { font-size:12px;color:#9DB5D5;line-height:1.5; }
.status.live { color:#55DCCB; }
.pulse { display:inline-block;width:7px;height:7px;border-radius:50%;background:#39D6C6;margin-right:6px; }

    div[data-testid="stButton"] button {
        min-height: 48px !important;
        height: 48px !important;
        padding: 0.6rem 1rem !important;
        font-size: 1rem !important;
        font-weight: 700 !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        box-sizing: border-box !important;
    }

</style>
</head>
<body>
<div class="wrap">
  <button id="mic" class="mic" aria-label="Start microphone" title="Stop speaking">🎙</button>
  <div class="texts">
    <div class="title">Live Voice Response</div>
    <div id="status" class="status">Tap the mic to start. Your speech will be transcribed in real time.</div>
  </div>
</div>
<script>
(() => {
  const mic = document.getElementById('mic');
  const statusEl = document.getElementById('status');
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  let recognition = null, active = false, finalText = '', lastSent = '';
  function sendValue(text) {
    if (text === lastSent) return;
    lastSent = text;
    window.parent.postMessage({isStreamlitMessage:true, type:'streamlit:setComponentValue',
      value:text, dataType:'json'}, '*');
  }
  function setStatus(text, live=false) {
    statusEl.textContent = text;
    statusEl.className = live ? 'status live' : 'status';
  }
  function stop() {
    active = false;
    mic.classList.remove('live');
    mic.setAttribute('aria-label','Start microphone');
    mic.title = 'Start speaking';
    try { if (recognition) recognition.stop(); } catch(e) {}
    setStatus('Speech stopped. Text transferred to response box.');
  }
  function start() {
    if (!SpeechRecognition) {
      setStatus('This browser does not support live speech recognition. Please use Google Chrome.');
      return;
    }
    finalText = '';
    lastSent = '';
    recognition = new SpeechRecognition();
    recognition.lang = 'en-US';
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.maxAlternatives = 1;
    recognition.onstart = () => {
      active = true;
      mic.classList.add('live');
      mic.setAttribute('aria-label','Stop microphone');
      mic.title = 'Stop speaking';
      setStatus('Listening… Text updates as you speak.', true);
    };
    recognition.onresult = (event) => {
      let interim = '';
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const transcript = event.results[i][0].transcript;
        if (event.results[i].isFinal) finalText += transcript.trim() + ' ';
        else interim += transcript;
      }
      const current = (finalText + interim).trim();
      if (current) sendValue(current);
      setStatus(current ? current : 'Listening…', true);
    };
    recognition.onerror = (event) => {
      if (event.error === 'not-allowed' || event.error === 'service-not-allowed') {
        setStatus('Microphone permission denied. Please allow microphone access in browser settings.');
      } else if (event.error !== 'no-speech' && event.error !== 'aborted') {
        setStatus('Speech recognition error: ' + event.error);
      }
    };
    recognition.onend = () => {
      if (active) {
        try { recognition.start(); } catch(e) {}
      } else {
        mic.classList.remove('live');
      }
    };
    try { recognition.start(); }
    catch(e) { setStatus('Microphone could not start. Refresh and try again.'); }
  }
  mic.addEventListener('click', () => active ? stop() : start());
  window.parent.postMessage({isStreamlitMessage:true, type:'streamlit:componentReady', apiVersion:1}, '*');
  window.addEventListener('message', (event) => {
    if (event.data && event.data.type === 'streamlit:render') {
      window.parent.postMessage({isStreamlitMessage:true, type:'streamlit:setFrameHeight', height:82}, '*');
    }
  });
})();
</script>
</body>
</html>""", encoding="utf-8")
    return components.declare_component(
        "pilotinterviewpro_live_speech",
        path=str(component_dir)
    )

live_speech_input = _live_speech_component()


# Page Configuration
st.set_page_config(
    page_title="PilotInterviewPro",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- SUPABASE CONNECTION & AUTHENTICATION ---
@st.cache_resource
def init_supabase() -> Client:
    url = st.secrets.get("SUPABASE_URL", "")
    key = st.secrets.get("SUPABASE_KEY", "")
    if not url or not key:
        return None
    return create_client(url, key)

supabase = init_supabase()

# 🎨 DESIGN SYSTEM — "Flight Deck"
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Barlow+Semi+Condensed:wght@500;600;700&family=IBM+Plex+Sans:wght@400;500;600&display=swap');

    :root {
        --panel: #0A1626;
        --panel-2: #12263F;
        --panel-line: #223A5A;
        --paper: #030D1D;
        --card: #0A1B32;
        --ink: #EAF2FF;
        --ink-soft: #9BB2D2;
        --line: #1B3A61;
        --amber: #FFB52E;
        --amber-deep: #D98B12;
        --green: #39D6C6;
        --red: #FF6675;
        --sky: #35BDF5;
    }

    html, body, [class*="css"] { font-family: 'IBM Plex Sans', sans-serif; }
    h1, h2, h3, h4, .display { font-family: 'Barlow Semi Condensed', sans-serif !important; letter-spacing: 0.1px; }

    .stApp { background: var(--paper) !important; color: var(--ink) !important; }
    header[data-testid="stHeader"] { background: transparent !important; }
    footer, #MainMenu { visibility: hidden; }
    .block-container { padding-top: 2rem; max-width: 100% !important; padding-left: 2rem !important; padding-right: 2rem !important; }

    /* ---------- Sidebar ---------- */
    section[data-testid="stSidebar"] {
        background: var(--panel) !important;
        border-right: 1px solid var(--panel-line);
    }
    section[data-testid="stSidebar"] label p,
    section[data-testid="stSidebar"] label { color: #C9D6E8 !important; font-weight: 500 !important; }
    section[data-testid="stSidebar"] hr { border-color: var(--panel-line) !important; }
    section[data-testid="stSidebar"] .stButton button {
        background: transparent !important;
        color: #E6EEF8 !important;
        border: 1px solid var(--panel-line) !important;
        border-radius: 8px !important;
        font-weight: 500;
    }
    section[data-testid="stSidebar"] .stButton button:hover {
        border-color: var(--amber) !important;
        color: var(--amber) !important;
    }
    .side-brand { padding: 6px 0 14px 0; }
    .side-brand .name { font-family: 'Barlow Semi Condensed', sans-serif; font-weight: 700; font-size: 1.55rem; color: #fff; line-height: 1.1; }
    .side-brand .name span { color: var(--amber); }
    .side-brand .who { color: #8FA8C8; font-size: 0.82rem; margin-top: 6px; word-break: break-all; }
    .side-stat { display:flex; justify-content:space-between; align-items:baseline; padding: 8px 0; border-bottom: 1px solid var(--panel-line); color:#8FA8C8; font-size:0.85rem; }
    .side-stat b { color:#fff; font-family:'Barlow Semi Condensed',sans-serif; font-size:1.15rem; font-weight:600; }

    /* ---------- Hero ---------- */
    .hero {
        position: relative; overflow: hidden;
        background: var(--panel);
        border-radius: 14px;
        padding: 36px 40px 40px 40px;
        margin-bottom: 20px;
        color: #fff;
        animation: heroIn .7s cubic-bezier(.16,1,.3,1) both;
    }
    .hero::before {
        content: ''; position: absolute; inset: 0;
        background:
            linear-gradient(180deg, transparent 0 58%, rgba(60,125,217,.22) 58.2%, rgba(60,125,217,.06) 100%),
            repeating-linear-gradient(90deg, rgba(255,255,255,.07) 0 1px, transparent 1px 48px);
        pointer-events: none;
    }
    .hero::after {
        content: ''; position: absolute; right: 40px; top: 0; bottom: 0; width: 3px;
        background: linear-gradient(180deg, var(--amber), rgba(242,168,29,0));
        opacity: .9;
    }
    .hero > * { position: relative; z-index: 1; }
    .hero .title { font-family:'Barlow Semi Condensed',sans-serif; font-size: 2.7rem; font-weight: 700; line-height: 1.05; margin: 0 0 10px 0; }
    .hero .sub { color: #B9C9DE; font-size: 1.02rem; max-width: 620px; line-height: 1.6; }
    .welcome { display:flex; align-items:center; gap:14px; margin-bottom: 22px; }
    .welcome .avatar {
        width: 46px; height: 46px; border-radius: 50%;
        background: var(--amber); color: #1A1203;
        display:flex; align-items:center; justify-content:center;
        font-family:'Barlow Semi Condensed',sans-serif; font-weight:700; font-size: 1.35rem;
        flex-shrink: 0;
    }
    .welcome .hi { color:#8FA8C8; font-size: 0.85rem; line-height: 1.2; }
    .welcome .name { font-family:'Barlow Semi Condensed',sans-serif; font-weight:600; font-size: 1.45rem; color:#fff; line-height: 1.2; }
    .hero.center { text-align: center; }
    .hero.center .sub { margin: 0 auto; }
    @keyframes heroIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: none; } }

    /* ---------- Instruments Strip ---------- */
    .strip {
        display: grid; grid-template-columns: repeat(4, 1fr);
        background: var(--card); border: 1px solid var(--line); border-radius: 12px;
        margin-bottom: 22px; overflow: hidden;
    }
    .strip .cell { padding: 16px 20px; border-right: 1px solid var(--line); }
    .strip .cell:last-child { border-right: none; }
    .strip .k { color: var(--ink-soft); font-size: 0.8rem; margin-bottom: 4px; }
    .strip .v { font-family:'Barlow Semi Condensed',sans-serif; font-size: 1.9rem; font-weight: 600; color: var(--ink); line-height: 1.1; font-variant-numeric: tabular-nums; }
    .strip .v small { font-size: 0.95rem; color: var(--ink-soft); font-weight: 500; margin-left: 4px; }

    /* ---------- Question Briefing Card ---------- */
    .brief {
        background: var(--card);
        border: 1px solid var(--line);
        border-left: 5px solid var(--amber);
        border-radius: 12px;
        padding: 26px 30px;
        margin-bottom: 22px;
    }
    .tags { display:flex; gap:8px; align-items:center; flex-wrap:wrap; margin-bottom: 14px; }
    .tag-cat { background: var(--panel); color:#fff; border-radius: 6px; padding: 5px 12px; font-size: 0.82rem; font-weight: 500; }
    .tag-diff { border-radius: 6px; padding: 5px 12px; font-size: 0.82rem; font-weight: 600; border: 1px solid; }
    .tag-diff.easy { color:#13795B; border-color:#9ADBC4; background:#EAF8F2; }
    .tag-diff.medium  { color:#8A5B00; border-color:#F2D18A; background:#FEF6E1; }
    .tag-diff.hard   { color:#A82F28; border-color:#EFB1AC; background:#FDEEEC; }
    .q-text { font-family:'Barlow Semi Condensed',sans-serif; font-size: 2.1rem !important; font-weight: 700 !important; color: var(--ink); line-height: 1.35; max-width: 100%; }

    /* ---------- Microphone Panel ---------- */
    .st-key-mic_card {
        background: var(--card);
        border: 1px solid var(--line);
        border-radius: 12px;
        padding: 18px 22px 8px 22px;
        margin-bottom: 18px;
    }
    .mic-h { font-family:'Barlow Semi Condensed',sans-serif; font-weight:600; font-size:1.15rem; color:var(--ink); }
    .mic-s { color: var(--ink-soft); font-size: 0.88rem; margin: 2px 0 10px 0; }

    /* ---------- Form Controls ---------- */
    .stTextArea label p { font-weight: 600; color: var(--ink); }
    .stTextArea textarea {
        background: var(--card) !important; color: var(--ink) !important;
        border: 1.5px solid var(--line) !important; border-radius: 10px !important;
        padding: 14px 16px !important; font-size: 1rem !important; line-height: 1.55;
    }
    .stTextArea textarea:focus { border-color: var(--sky) !important; box-shadow: 0 0 0 3px rgba(60,125,217,.18) !important; }
    .stTextInput input { border-radius: 10px !important; }

    .stButton button { border-radius: 10px; font-weight: 600; padding: 0.55rem 1rem; transition: background .15s, border-color .15s; }
    .stButton button[kind="primary"], .stButton button[data-testid="stBaseButton-primary"] {
        background: var(--amber) !important; color: #1A1203 !important; border: 1px solid var(--amber) !important;
    }
    .stButton button[kind="primary"]:hover, .stButton button[data-testid="stBaseButton-primary"]:hover {
        background: #FFBD3A !important; border-color: #FFBD3A !important; color:#1A1203 !important;
    }
    .stButton button[kind="secondary"], .stButton button[data-testid="stBaseButton-secondary"] {
        background: var(--card); color: var(--ink); border: 1.5px solid var(--line);
    }
    .stButton button[kind="secondary"]:hover, .stButton button[data-testid="stBaseButton-secondary"]:hover {
        border-color: var(--ink); color: var(--ink);
    }
    button:focus-visible { outline: 3px solid var(--sky) !important; outline-offset: 2px; }

    /* ---------- Report Card / Score Gauge ---------- */
    .report {
        background: var(--card); border: 1px solid var(--line); border-radius: 12px;
        padding: 26px 30px; margin-top: 8px; margin-bottom: 22px;
        display: grid; grid-template-columns: 220px 1fr; gap: 28px; align-items: center;
    }
    .gauge { text-align: center; }
    .gauge svg { width: 100%; max-width: 220px; height: auto; display:block; margin: 0 auto; }
    .gauge .num { font-family:'Barlow Semi Condensed',sans-serif; font-size: 2.6rem; font-weight: 700; fill: var(--ink); }
    .gauge .of  { font-size: 0.8rem; fill: var(--ink-soft); }
    .verdict .label { font-family:'Barlow Semi Condensed',sans-serif; font-size: 1.6rem; font-weight: 700; margin-bottom: 4px; }
    .verdict .desc { color: var(--ink-soft); line-height: 1.55; margin-bottom: 14px; }
    .chips { display:flex; flex-wrap:wrap; gap:6px; margin-top: 6px; }
    .chips-title { font-size: 0.8rem; color: var(--ink-soft); margin-top: 10px; font-weight: 600; }
    .chip { border-radius: 6px; padding: 4px 10px; font-size: 0.82rem; font-weight: 500; border: 1px solid; }
    .chip.ok   { color:#13795B; background:#EAF8F2; border-color:#9ADBC4; }
    .chip.miss { color:#7A5A12; background:#FEF6E1; border-color:#F2D18A; }

    .model-answer {
        background: var(--panel); color: #E6EEF8; border-radius: 12px;
        padding: 22px 28px; margin-bottom: 22px; border-left: 5px solid var(--green);
    }
    .model-answer .h { font-family:'Barlow Semi Condensed',sans-serif; font-weight:600; font-size:1.05rem; color: var(--green); margin-bottom: 8px; }
    .model-answer .t { line-height: 1.7; font-size: 1rem; max-width: 100%; }

    /* ---------- Tip Box ---------- */
    .tip {
        background: transparent; border: 1px dashed #B5C0CF; border-radius: 12px;
        padding: 16px 22px; color: var(--ink-soft); font-size: 0.92rem; line-height: 1.6;
    }
    .tip b { color: var(--ink); }

    /* ---------- Flight Progress ---------- */
    .flight {
        background: var(--card); border: 1px solid var(--line); border-radius: 12px; padding: 22px 24px;
    }
    .flight .h { font-family:'Barlow Semi Condensed',sans-serif; font-weight:600; font-size:1.1rem; color: var(--ink); margin-bottom: 14px; }
    .flight .pct { font-family:'Barlow Semi Condensed',sans-serif; font-size: 2.6rem; font-weight: 700; color: var(--ink); line-height: 1; font-variant-numeric: tabular-nums; }
    .flight .track { position: relative; height: 4px; background: var(--line); border-radius: 4px; margin: 22px 8px 10px 8px; }
    .flight .fill  { position:absolute; left:0; top:0; bottom:0; background: var(--amber); border-radius: 4px; }
    .flight .dot   { position:absolute; top:50%; width: 16px; height: 16px; border-radius: 50%; background: var(--panel); border: 3px solid var(--amber); transform: translate(-50%, -50%); }
    .flight .end   { position:absolute; right:-8px; top:50%; width: 10px; height: 10px; background: var(--ink); transform: translateY(-50%) rotate(45deg); }
    .flight .legend { display:flex; justify-content:space-between; color: var(--ink-soft); font-size: 0.8rem; margin: 0 4px; }
    .flight .note { margin-top: 14px; color: var(--ink-soft); font-size: 0.9rem; line-height: 1.5; }
    .flight .note b { color: var(--ink); }

    /* ---------- Cockpit Theme ---------- */
    .stApp {
        background:
            radial-gradient(ellipse at 58% 0%, rgba(24,75,132,.22), transparent 42%),
            radial-gradient(ellipse at 100% 65%, rgba(8,45,82,.22), transparent 36%),
            #030D1D !important;
        color: #EAF2FF !important;
    }
    .block-container { max-width: 100% !important; padding-left: 2rem !important; padding-right: 2rem !important; padding-top: 1.5rem; padding-bottom: 3rem; }
    [data-testid="stMain"] { background: transparent !important; }
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #07172C 0%, #061225 100%) !important;
        border-right: 1px solid #1B3A61 !important;
    }
    section[data-testid="stSidebar"] * { color: #D9E7FC; }
    .hero {
        background:
            linear-gradient(90deg, rgba(3,15,34,.98) 0%, rgba(5,25,53,.88) 48%, rgba(6,29,57,.50) 100%),
            radial-gradient(ellipse at 75% 35%, rgba(43,120,205,.30), transparent 42%),
            linear-gradient(135deg, #0A2344, #07152B) !important;
        border: 1px solid #28517D !important;
        border-radius: 26px !important;
        box-shadow: 0 20px 55px rgba(0,0,0,.28), inset 0 1px rgba(255,255,255,.05);
        overflow: hidden;
    }
    .brief, .st-key-mic_card, .report, .flight, .tip, .model-answer {
        background: linear-gradient(145deg, rgba(12,33,59,.98), rgba(7,23,43,.98)) !important;
        border: 1px solid #24486F !important;
        border-radius: 23px !important;
        box-shadow: 0 14px 34px rgba(0,0,0,.20), inset 0 1px rgba(255,255,255,.035) !important;
        color: #EAF2FF !important;
    }
    .brief { border-left: 3px solid var(--amber) !important; padding: 28px 30px !important; }
    .q-text, .mic-h, .flight .h, .flight .pct, .flight .note b,
    .stTextArea label p, .verdict .label, .chips-title, .tip b {
        color: #EDF5FF !important;
    }
    .tag-cat { background: #17365E !important; border: 1px solid #315A88; border-radius: 999px !important; }
    .tag-diff.easy { color: #65E7C1 !important; border-color: #226C65 !important; background: #0C393B !important; }
    .tag-diff.medium { color: #FFD16A !important; border-color: #745B29 !important; background: #3A2D17 !important; }
    .tag-diff.hard { color: #FF9DA6 !important; border-color: #783D4A !important; background: #3A1E2B !important; }
    
    .stTextArea textarea, .stTextInput input {
        background: #06172D !important; color: #EAF2FF !important;
        border: 1px solid #254A75 !important; border-radius: 17px !important;
    }

    div[data-testid="stButton"] button {
        min-height: 48px !important;
        height: 48px !important;
        padding: 0.6rem 1rem !important;
        font-size: 1rem !important;
        font-weight: 700 !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        box-sizing: border-box !important;
    }

    .st-key-mic_card {
        background: linear-gradient(145deg, #0C213B 0%, #07172B 100%) !important;
        border: 1px solid #24486F !important;
        border-radius: 20px !important;
        padding: 12px 16px 10px !important;
    }
    .st-key-mic_card iframe {
        display: block !important;
        height: 84px !important;
        min-height: 84px !important;
        border: 0 !important;
    }
    .brief .q-text, .q-text { font-size: 1.85rem !important; line-height: 1.35 !important; font-weight: 700 !important; }
</style>
""", unsafe_allow_html=True)

# Helper Functions
def sanitize_text(text: str) -> str:
    if not text: return ""
    return text.strip().lower()

def is_flexible_match(keyword: str, clean_answer: str) -> bool:
    clean_kw = sanitize_text(str(keyword))
    clean_kw = re.sub(r'[^\w\s]', '', clean_kw)
    if not clean_kw: return False
    if clean_kw in clean_answer: return True
    words_in_kw = clean_kw.split()
    if len(words_in_kw) > 1:
        matched_parts = sum(1 for w in words_in_kw if len(w) >= 3 and (w[:4] if len(w) >= 4 else w) in clean_answer)
        return matched_parts >= 1
    else:
        single_w = words_in_kw[0]
        return (single_w[:4] in clean_answer) if len(single_w) >= 4 else (single_w in clean_answer)

def calculate_score(user_answer: str, keywords: list) -> dict:
    if not user_answer or not user_answer.strip():
        return {"score": 0, "matched_count": 0, "matched_keywords": [], "missing_keywords": keywords}
    clean_answer = re.sub(r'[^\w\s]', ' ', sanitize_text(user_answer))
    matched_keywords = [kw for kw in keywords if is_flexible_match(kw, clean_answer)]
    missing_keywords = [kw for kw in keywords if kw not in matched_keywords]
    match_count = len(matched_keywords)
    score = 100 if match_count >= 4 else (80 if match_count == 3 else (60 if match_count == 2 else (30 if match_count == 1 else 0)))
    return {"score": score, "matched_count": match_count, "matched_keywords": matched_keywords, "missing_keywords": missing_keywords}

@st.cache_data(ttl=60)
def load_questions():
    try:
        with open("questions.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

questions_data = load_questions()

# Session State Initialization
if "user" not in st.session_state: st.session_state.user = None
if "session" not in st.session_state: st.session_state.session = None
if "sorulan_ids" not in st.session_state: st.session_state.sorulan_ids = []
if "puanlar" not in st.session_state: st.session_state.puanlar = []
if "mevcut_soru" not in st.session_state: st.session_state.mevcut_soru = None
if "son_analiz" not in st.session_state: st.session_state.son_analiz = None
if "secilen_kategori" not in st.session_state: st.session_state.secilen_kategori = "All Categories"

if supabase and not st.session_state.user:
    try:
        curr_session = supabase.auth.get_session()
        if curr_session and curr_session.user:
            st.session_state.user = curr_session.user
            st.session_state.session = curr_session
    except Exception:
        pass

def save_user_progress():
    if supabase and st.session_state.user:
        try:
            supabase.table("user_progress").upsert({
                "user_id": st.session_state.user.id,
                "email": st.session_state.user.email,
                "sorulan_ids": st.session_state.sorulan_ids,
                "puanlar": st.session_state.puanlar
            }).execute()
        except Exception:
            pass

def load_user_progress():
    if supabase and st.session_state.user:
        try:
            res = supabase.table("user_progress").select("*").eq("user_id", st.session_state.user.id).execute()
            if res.data and len(res.data) > 0:
                data = res.data[0]
                st.session_state.sorulan_ids = data.get("sorulan_ids", []) or []
                st.session_state.puanlar = data.get("puanlar", []) or []
        except Exception:
            pass

def reset_user_progress():
    st.session_state.sorulan_ids = []
    st.session_state.puanlar = []
    st.session_state.son_analiz = None
    save_user_progress()

def puan_kaydet(soru_id, puan):
    an = st.session_state.son_analiz
    if an and an.get("soru_id") == soru_id and st.session_state.puanlar:
        st.session_state.puanlar[-1] = puan
    else:
        st.session_state.puanlar.append(puan)

# Score Indicator Helpers
SKOR_BILGI = {
    100: ("Excellent", "#2FBF8F", "Your response aligns fully with the expected answer. Maintain this standard."),
    80:  ("Very Good", "#2FBF8F", "Your answer covers most key areas. Add the missing concepts to reach a 100% score."),
    60:  ("Moderate", "#F2A81D", "The core idea is present, but key technical details are missing."),
    30:  ("Needs Work", "#D8483F", "Significant gaps in the response. Review the model answer and try again."),
    0:   ("Inadequate", "#D8483F", "Targeted technical concepts were not found in your response."),
}

def gauge_svg(puan: int, renk: str) -> str:
    uzunluk = 251.33
    dolu = uzunluk * (puan / 100)
    return f"""
    <svg viewBox="0 0 200 124" role="img" aria-label="Score {puan} / 100">
        <path d="M20 104 A80 80 0 0 1 180 104" fill="none" stroke="#E3E8EF" stroke-width="14" stroke-linecap="round"/>
        <path class="arc" d="M20 104 A80 80 0 0 1 180 104" fill="none" stroke="{renk}" stroke-width="14" stroke-linecap="round"
              stroke-dasharray="{dolu:.1f} {uzunluk:.1f}"/>
        <text x="100" y="92" text-anchor="middle" class="num">{puan}</text>
        <text x="100" y="114" text-anchor="middle" class="of">/ 100</text>
    </svg>"""

def chips_html(items, css_class):
    safe_class = "ok" if css_class == "ok" else "miss"
    return "".join(
        f'<span class="chip {safe_class}">{html.escape(str(k))}</span>'
        for k in items
    )

# --- LOGIN / SIGNUP SCREEN ---
if not st.session_state.user:
    st.markdown("""
    <div class="hero center login-hero">
        <div class="login-orbit" aria-hidden="true">
            <span class="orbit-ring ring-a"></span>
            <span class="orbit-ring ring-b"></span>
            <span class="orbit-plane">✈</span>
            <span class="orbit-dot dot-a"></span><span class="orbit-dot dot-b"></span>
        </div>
        <div class="login-kicker"><span class="live-dot"></span> FLIGHT DECK · INTERVIEW TRAINING</div>
        <div class="title">✈️ PilotInterviewPro</div>
        <div class="sub">Prepare for airline technical interviews. Your progress is saved to your account.</div>
        <div class="login-widgets">
            <div class="login-widget"><span class="widget-icon">◉</span><span><b>Live Practice</b><small>Respond by speaking</small></span><i class="widget-pulse"></i></div>
            <div class="login-widget"><span class="widget-icon">⌁</span><span><b>Flight Instruments</b><small>Track your progress</small></span><span class="mini-bars"><i></i><i></i><i></i><i></i><i></i></span></div>
            <div class="login-widget"><span class="widget-icon">✦</span><span><b>Smart Evaluation</b><small>Feedback on your answer</small></span><span class="widget-check">✓</span></div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    col_auth1, col_auth2, col_auth3 = st.columns([1, 1.7, 1])
    with col_auth2:
        tab_login, tab_signup = st.tabs(["Log In", "Sign Up"])

        with tab_login:
            login_email = st.text_input("Email", key="l_email")
            login_pass = st.text_input("Password", type="password", key="l_pass")
            if st.button("Log In", type="primary", use_container_width=True):
                if supabase:
                    try:
                        res = supabase.auth.sign_in_with_password({"email": login_email, "password": login_pass})
                        st.session_state.user = res.user
                        st.session_state.session = res.session
                        load_user_progress()
                        st.success("Login successful!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Login error: {e}")
                else:
                    st.error("Supabase connection missing (Secrets).")

        with tab_signup:
            signup_email = st.text_input("Email", key="s_email")
            signup_pass = st.text_input("Password (at least 6 characters)", type="password", key="s_pass")
            if st.button("Create Account", use_container_width=True):
                if supabase:
                    try:
                        res = supabase.auth.sign_up({"email": signup_email, "password": signup_pass})
                        st.session_state.user = res.user
                        st.session_state.session = res.session
                        save_user_progress()
                        st.success("Account created successfully!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Sign up error: {e}")
    st.stop()

if st.session_state.user and not st.session_state.sorulan_ids and not st.session_state.puanlar:
    load_user_progress()

# --- MAIN APPLICATION FLOW ---

def yeni_soru_getir(kategori_filtresi):
    if kategori_filtresi == "All Categories":
        filtre = questions_data
    else:
        filtre = [q for q in questions_data if q.get("category") == kategori_filtresi]

    if not filtre:
        st.session_state.mevcut_soru = None
        return

    kullanilabilir = [q for q in filtre if q["id"] not in st.session_state.sorulan_ids]
    if not kullanilabilir:
        st.session_state.sorulan_ids = [q_id for q_id in st.session_state.sorulan_ids if q_id not in [q["id"] for q in filtre]]
        kullanilabilir = filtre

    if kullanilabilir:
        secilen = random.choice(kullanilabilir)
        st.session_state.mevcut_soru = secilen
        st.session_state.sorulan_ids.append(secilen["id"])
        st.session_state.son_analiz = None
        save_user_progress()

toplam_soru = len(questions_data)
tamamlanan = len(st.session_state.puanlar)
ort_skor = (sum(st.session_state.puanlar) / tamamlanan) if tamamlanan > 0 else 0

# Sidebar
st.sidebar.markdown(f"""
<div class="side-brand">
    <div class="name">✈️ Pilot<span>Interview</span>Pro</div>
    <div class="who">{html.escape(str(st.session_state.user.email or ""))}</div>
</div>
""", unsafe_allow_html=True)

kategoriler = ["All Categories"] + sorted(list(set(q["category"] for q in questions_data))) if questions_data else []

def on_kategori_change():
    yeni_kat = st.session_state.kat_select_box
    st.session_state.secilen_kategori = yeni_kat
    yeni_soru_getir(yeni_kat)

kat_index = kategoriler.index(st.session_state.secilen_kategori) if st.session_state.secilen_kategori in kategoriler else 0

secilen_kategori = st.sidebar.selectbox("Interview Category", kategoriler, index=kat_index, key="kat_select_box", on_change=on_kategori_change)

st.sidebar.markdown(f"""
<div style="margin-top:14px;">
    <div class="side-stat"><span>Answered</span><b>{tamamlanan}</b></div>
    <div class="side-stat"><span>Average Score</span><b>%{ort_skor:.0f}</b></div>
    <div class="side-stat"><span>Target</span><b>%80+</b></div>
</div>
""", unsafe_allow_html=True)

st.sidebar.markdown("<div style='height:18px'></div>", unsafe_allow_html=True)

if st.sidebar.button("Reset Progress", use_container_width=True, help="Resets all your answer and score history."):
    reset_user_progress()
    st.rerun()

st.sidebar.markdown("""
<div class="radar"><span class="blip b1"></span><span class="blip b2"></span></div>
""", unsafe_allow_html=True)

if st.sidebar.button("Log Out", use_container_width=True):
    if supabase:
        try:
            supabase.auth.sign_out()
        except Exception:
            pass
    st.session_state.user = None
    st.session_state.session = None
    st.session_state.sorulan_ids = []
    st.session_state.puanlar = []
    st.rerun()

if st.session_state.mevcut_soru is None and questions_data:
    yeni_soru_getir(st.session_state.secilen_kategori)

def display_name(email: str) -> str:
    local = (email or "").split("@")[0]
    words = [w for w in re.split(r"[._\-\s]+", local) if w]
    out = [w.capitalize() for w in words]
    return " ".join(out) if out else "Pilot Candidate"

kullanici_adi = display_name(st.session_state.user.email)
avatar_harf = html.escape(kullanici_adi[0])
kullanici_adi_html = html.escape(kullanici_adi)

# Hero Banner
st.markdown(f"""
<div class="hero">
    <div class="cloud c1"></div><div class="cloud c2"></div>
    <div class="plane"><svg viewBox="0 0 120 44" aria-hidden="true"><path fill="#fff" d="M4 24 Q4 19 14 19 L92 19 Q113 20 117 24 Q113 28 92 29 L14 29 Q4 29 4 24Z"/><path fill="#fff" d="M12 19 L3 5 L16 5 L30 19Z"/><path fill="#fff" d="M50 27 L72 41 L84 41 L70 27Z"/><path fill="#fff" opacity=".7" d="M52 20 L70 9 L80 9 L68 20Z"/><circle cx="100" cy="23.5" r="1.6" fill="#0A1626"/><circle cx="92" cy="23.5" r="1.6" fill="#0A1626"/><circle cx="84" cy="23.5" r="1.6" fill="#0A1626"/></svg></div>
    <div class="welcome">
        <div class="avatar">{avatar_harf}</div>
        <div>
            <div class="hi">Welcome back</div>
            <div class="name">{kullanici_adi_html}</div>
        </div>
    </div>
    <div class="title">Airline Technical Interview Prep</div>
    <div class="sub">Answer technical aviation questions using voice input with precise terminology. Your progress is saved automatically.</div>
</div>
""", unsafe_allow_html=True)

# Instruments Strip
st.markdown(f"""
<div class="strip">
    <div class="cell"><div class="k">Total Questions</div><div class="v">{toplam_soru}</div></div>
    <div class="cell"><div class="k">Categories</div><div class="v">{max(len(kategoriler)-1, 0)}</div></div>
    <div class="cell"><div class="k">Average Score</div><div class="v">%{ort_skor:.0f}</div></div>
    <div class="cell"><div class="k">Target Score</div><div class="v">%80<small>and above</small></div></div>
</div>
""", unsafe_allow_html=True)

col_left, col_right = st.columns([2.5, 1], gap="large")

with col_left:
    if st.session_state.mevcut_soru:
        soru = st.session_state.mevcut_soru
        input_key = f"answer_input_{soru.get('id')}"

        zorluk = str(soru.get('difficulty', 'Medium'))
        zorluk_css = {"Easy": "easy", "Medium": "medium", "Hard": "hard"}.get(zorluk, "medium")
        kategori_html = html.escape(str(soru.get('category', 'General')))
        zorluk_html = html.escape(zorluk)
        soru_html = html.escape(str(soru.get('question', '')))

        st.markdown(f"""
        <div class="brief">
            <div class="tags">
                <span class="tag-cat">{kategori_html}</span>
                <span class="tag-diff {zorluk_css}">{zorluk_html}</span>
            </div>
            <div class="q-text">{soru_html}</div>
        </div>
        """, unsafe_allow_html=True)

        model_answer_text = soru.get("model_answer")
        if not model_answer_text:
            kw_list = soru.get("keywords", [])
            model_answer_text = "Key concepts expected for this question: " + ", ".join(kw_list) + "."

        with st.container(key="mic_card"):
            st.markdown("""
            <div class="mic-h">Voice Response</div>
            <div class="mic-s">Turn on the mic and speak. Your speech is transcribed in real-time without storing audio files.</div>
            """, unsafe_allow_html=True)
            live_text = live_speech_input(
                key=f"live_{soru.get('id')}_{len(st.session_state.sorulan_ids)}",
                default=""
            )
            if isinstance(live_text, str) and live_text.strip():
                st.session_state[input_key] = live_text

        kullanici_cevabi = st.text_area("Transcribed / typed response", placeholder="Your speech will appear here automatically. You can also edit it manually.", height=130, key=input_key)

        btn_c1, btn_c2 = st.columns([1, 1])
        with btn_c1:
            if st.button("Evaluate Answer", type="primary", use_container_width=True):
                if kullanici_cevabi.strip():
                    keywords = soru.get("keywords", [])
                    eval_result = calculate_score(kullanici_cevabi, keywords)
                    puan = eval_result["score"]
                    puan_kaydet(soru.get("id"), puan)
                    st.session_state.son_analiz = {
                        "soru_id": soru.get("id"),
                        "puan": puan,
                        "metin": kullanici_cevabi,
                        "model_answer": model_answer_text,
                        "matched": eval_result["matched_keywords"],
                        "missing": eval_result["missing_keywords"],
                    }
                    save_user_progress()
                    st.rerun()
                else:
                    st.warning("Please speak or type a response first.")

        with btn_c2:
            if st.button("Next Question", use_container_width=True):
                yeni_soru_getir(st.session_state.secilen_kategori)
                st.rerun()

        if st.session_state.son_analiz:
            res = st.session_state.son_analiz
            puan = res["puan"]
            etiket, renk, aciklama = SKOR_BILGI.get(puan, SKOR_BILGI[0])

            matched = res.get("matched", [])
            missing = res.get("missing", [])
            kw_html = ""
            if matched:
                kw_html += f'<div class="chips-title">Matched Technical Concepts</div><div class="chips">{chips_html(matched, "ok")}</div>'
            if missing:
                kw_html += f'<div class="chips-title">Missing Concepts to Include</div><div class="chips">{chips_html(missing, "miss")}</div>'

            model_answer_html = html.escape(str(res.get('model_answer', '')))
            etiket_html = html.escape(str(etiket))
            aciklama_html = html.escape(str(aciklama))
            st.markdown(f"""
            <div class="report">
                <div class="gauge">{gauge_svg(puan, renk)}</div>
                <div class="verdict">
                    <div class="label" style="color:{renk};">{etiket_html}</div>
                    <div class="desc">{aciklama_html}</div>
                    {kw_html}
                </div>
            </div>
            <div class="model-answer">
                <div class="h">Model Interview Answer</div>
                <div class="t">{model_
