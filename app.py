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


# --- LIVE SPEECH RECOGNITION (no audio file is saved) ---
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
html, body { margin:0 !important; padding:0 !important; width:100%; min-height:0 !important; background:rgba(255,255,255,0) !important; background-color:transparent !important; color:#0F172A; overflow:hidden; }
body { font-family:Arial,sans-serif; }
.wrap { display:flex; align-items:center; gap:14px; padding:5px 2px; min-height:72px; background:transparent !important; }
.mic { width:60px;height:60px;flex:0 0 60px;border-radius:50%;border:2px solid #2563EB;
 background:radial-gradient(circle at 32% 24%,#3B82F6 0%,#1D4ED8 42%,#1E40AF 100%);
 color:#fff;font-size:27px;cursor:pointer;box-shadow:0 0 0 6px rgba(37,99,235,.12),0 0 28px rgba(29,78,216,.25);
 transition:transform .18s,box-shadow .18s; }
.mic:hover { transform:scale(1.05);box-shadow:0 0 0 9px rgba(37,99,235,.18),0 0 38px rgba(29,78,216,.35); }
.mic.live { background:radial-gradient(circle at 32% 24%,#EF4444 0%,#DC2626 48%,#991B1B 100%);border-color:#FCA5A5; }
.texts { min-width:0; }
.title { font-size:14px;font-weight:700;margin-bottom:6px;color:#0F172A; }
.status { font-size:12px;color:#0F172A;font-weight:500;line-height:1.5; }
.status.live { color:#059669; }
.pulse { display:inline-block;width:7px;height:7px;border-radius:50%;background:#10B981;margin-right:6px; }
</style>
</head>
<body>
<div class="wrap">
  <button id="mic" class="mic" aria-label="Start microphone" title="Start speaking">🎙</button>
  <div class="texts">
    <div class="title">Live voice answer</div>
    <div id="status" class="status">Tap the mic to start. Your speech is transcribed in real time.</div>
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
      setStatus('This browser does not support live speech recognition. Please use the latest version of Chrome.');
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
        setStatus('Microphone permission denied. Allow microphone access in your browser settings.');
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
    catch(e) { setStatus('Could not start the microphone. Refresh the page and try again.'); }
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


# Page configuration
st.set_page_config(
    page_title="PILOTPREP",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- SUPABASE CONNECTION AND SESSION MANAGEMENT ---
@st.cache_resource
def init_supabase() -> Client:
    url = st.secrets.get("SUPABASE_URL", "")
    key = st.secrets.get("SUPABASE_KEY", "")
    if not url or not key:
        return None
    return create_client(url, key)

supabase = init_supabase()

# 🎨 DESIGN SYSTEM — "Clean Sky / Light Mode with Dark Navy Text"
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Barlow+Semi+Condensed:wght@500;600;700&family=IBM+Plex+Sans:wght@400;500;600&display=swap');

    :root {
        --panel: #F8FAFC;
        --panel-2: #F1F5F9;
        --panel-line: #CBD5E1;
        --paper: #FFFFFF;
        --card: #FFFFFF;
        --ink: #0F172A;
        --ink-soft: #1E293B;
        --line: #E2E8F0;
        --amber: #D97706;
        --amber-deep: #B45309;
        --green: #059669;
        --red: #DC2626;
        --sky: #0284C7;
    }

    html, body, [class*="css"] { font-family: 'IBM Plex Sans', sans-serif; color: #0F172A !important; }
    h1, h2, h3, h4, .display { font-family: 'Barlow Semi Condensed', sans-serif !important; letter-spacing: 0.1px; color: #0F172A !important; }

    .stApp { background: var(--paper) !important; color: #0F172A !important; }
    header[data-testid="stHeader"] { background: transparent !important; }
    footer, #MainMenu { visibility: hidden; }
    .block-container { padding-top: 2rem; max-width: 100% !important; padding-left: 2rem !important; padding-right: 2rem !important; }

    /* ---------- Sidebar (cockpit panel) ---------- */
    section[data-testid="stSidebar"] {
        background: var(--panel) !important;
        border-right: 1px solid var(--panel-line);
    }
    section[data-testid="stSidebar"] label p,
    section[data-testid="stSidebar"] label { color: #0F172A !important; font-weight: 700 !important; }
    section[data-testid="stSidebar"] hr { border-color: var(--panel-line) !important; }
    section[data-testid="stSidebar"] .stButton button {
        background: #FFFFFF !important;
        color: #0F172A !important;
        border: 1px solid var(--panel-line) !important;
        border-radius: 8px !important;
        font-weight: 600;
    }
    section[data-testid="stSidebar"] .stButton button:hover {
        border-color: var(--amber) !important;
        color: var(--amber) !important;
    }
    .side-brand { padding: 6px 0 14px 0; }
    .side-brand .name { font-family: 'Barlow Semi Condensed', sans-serif; font-weight: 700; font-size: 1.55rem; color: #0F172A; line-height: 1.1; }
    .side-brand .name span { color: var(--amber); }
    .side-brand .who { color: #1E293B; font-size: 0.82rem; margin-top: 6px; word-break: break-all; font-weight: 500; }
    .side-stat { display:flex; justify-content:space-between; align-items:baseline; padding: 8px 0; border-bottom: 1px solid var(--panel-line); color:#1E293B; font-size:0.85rem; font-weight:600; }
    .side-stat b { color:#0F172A; font-family:'Barlow Semi Condensed',sans-serif; font-size:1.15rem; font-weight:700; }

    /* ---------- Hero ---------- */
    .hero {
        position: relative; overflow: hidden;
        background: #F1F5F9;
        border-radius: 14px;
        padding: 36px 40px 40px 40px;
        margin-bottom: 20px;
        color: #0F172A;
        animation: heroIn .7s cubic-bezier(.16,1,.3,1) both;
    }
    .hero::before {
        content: ''; position: absolute; inset: 0;
        background:
            linear-gradient(180deg, transparent 0 58%, rgba(2,132,199,.08) 58.2%, rgba(2,132,199,.02) 100%),
            repeating-linear-gradient(90deg, rgba(15,23,42,.03) 0 1px, transparent 1px 48px);
        pointer-events: none;
    }
    .hero::after {
        content: ''; position: absolute; right: 40px; top: 0; bottom: 0; width: 3px;
        background: linear-gradient(180deg, var(--amber), rgba(217,119,6,0));
        opacity: .9;
    }
    .hero > * { position: relative; z-index: 1; }
    .hero .title { font-family:'Barlow Semi Condensed',sans-serif; font-size: 2.7rem; font-weight: 700; line-height: 1.05; margin: 0 0 10px 0; color: #0F172A !important; }
    .hero .sub { color: #1E293B !important; font-size: 1.02rem; max-width: 620px; line-height: 1.6; font-weight: 500; }
    .welcome { display:flex; align-items:center; gap:14px; margin-bottom: 22px; }
    .welcome .avatar {
        width: 46px; height: 46px; border-radius: 50%;
        background: var(--amber); color: #FFFFFF;
        display:flex; align-items:center; justify-content:center;
        font-family:'Barlow Semi Condensed',sans-serif; font-weight:700; font-size: 1.35rem;
        flex-shrink: 0;
    }
    .welcome .hi { color:#1E293B !important; font-size: 0.85rem; line-height: 1.2; font-weight: 600; }
    .welcome .name { font-family:'Barlow Semi Condensed',sans-serif; font-weight:600; font-size: 1.45rem; color:#0F172A !important; line-height: 1.2; }
    .hero.center { text-align: center; }
    .hero.center .sub { margin: 0 auto; }
    @keyframes heroIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: none; } }

    /* ---------- Instrument strip (summary metrics) ---------- */
    .strip {
        display: grid; grid-template-columns: repeat(4, 1fr);
        background: var(--card); border: 1px solid var(--line); border-radius: 12px;
        margin-bottom: 22px; overflow: hidden;
    }
    .strip .cell { padding: 16px 20px; border-right: 1px solid var(--line); }
    .strip .cell:last-child { border-right: none; }
    .strip .k { color: #1E293B !important; font-size: 0.8rem; margin-bottom: 4px; font-weight: 600; }
    .strip .v { font-family:'Barlow Semi Condensed',sans-serif; font-size: 1.9rem; font-weight: 700; color: #0F172A !important; line-height: 1.1; font-variant-numeric: tabular-nums; }
    .strip .v small { font-size: 0.95rem; color: #1E293B !important; font-weight: 600; margin-left: 4px; }

    /* ---------- Question card (briefing) ---------- */
    .brief {
        background: var(--card);
        border: 1px solid var(--line);
        border-left: 5px solid var(--amber);
        border-radius: 12px;
        padding: 26px 30px;
        margin-bottom: 22px;
    }
    .tags { display:flex; gap:8px; align-items:center; flex-wrap:wrap; margin-bottom: 14px; }
    .tag-cat { background: #E2E8F0; color:#0F172A !important; border-radius: 6px; padding: 5px 12px; font-size: 0.82rem; font-weight: 700; }
    .tag-diff { border-radius: 6px; padding: 5px 12px; font-size: 0.82rem; font-weight: 700; border: 1px solid; }
    .tag-diff.easy   { color:#047857 !important; border-color:#A7F3D0; background:#ECFDF5; }
    .tag-diff.medium { color:#B45309 !important; border-color:#FDE68A; background:#FEF3C7; }
    .tag-diff.hard   { color:#B91C1C !important; border-color:#FECACA; background:#FEF2F2; }
    .q-text { font-family:'Barlow Semi Condensed',sans-serif; font-size: 2.1rem !important; font-weight: 700 !important; color: #0F172A !important; line-height: 1.35; max-width: 100%; }

    /* ---------- Microphone panel ---------- */
    .st-key-mic_card {
        background: var(--card);
        border: 1px solid var(--line);
        border-radius: 12px;
        padding: 18px 22px 8px 22px;
        margin-bottom: 18px;
    }
    .mic-h { font-family:'Barlow Semi Condensed',sans-serif; font-weight:700; font-size:1.15rem; color:#0F172A !important; }
    .mic-s { color: #1E293B !important; font-size: 0.88rem; margin: 2px 0 10px 0; font-weight: 500; }

    /* ---------- Form elements ---------- */
    .stTextArea label p { font-weight: 700 !important; color: #0F172A !important; }
    .stTextArea textarea {
        background: #FFFFFF !important; color: #0F172A !important;
        border: 1.5px solid #CBD5E1 !important; border-radius: 10px !important;
        padding: 14px 16px !important; font-size: 1rem !important; line-height: 1.55; font-weight: 500;
    }
    .stTextArea textarea::placeholder { color: #64748B !important; }
    .stTextArea textarea:focus { border-color: var(--sky) !important; box-shadow: 0 0 0 3px rgba(2,132,199,.18) !important; }
    .stTextInput input { border-radius: 10px !important; color: #0F172A !important; }

    .stButton button { border-radius: 10px; font-weight: 700; padding: 0.55rem 1rem; transition: background .15s, border-color .15s; }
    .stButton button[kind="primary"], .stButton button[data-testid="stBaseButton-primary"] {
        background: var(--amber) !important; color: #FFFFFF !important; border: 1px solid var(--amber) !important;
    }
    .stButton button[kind="primary"]:hover, .stButton button[data-testid="stBaseButton-primary"]:hover {
        background: #B45309 !important; border-color: #B45309 !important; color:#FFFFFF !important;
    }
    .stButton button[kind="secondary"], .stButton button[data-testid="stBaseButton-secondary"] {
        background: var(--card); color: #0F172A !important; border: 1.5px solid #CBD5E1;
    }
    .stButton button[kind="secondary"]:hover, .stButton button[data-testid="stBaseButton-secondary"]:hover {
        border-color: #0F172A; color: #0F172A !important;
    }
    button:focus-visible { outline: 3px solid var(--sky) !important; outline-offset: 2px; }

    /* ---------- Report card (score gauge) ---------- */
    .report {
        background: var(--card); border: 1px solid var(--line); border-radius: 12px;
        padding: 26px 30px; margin-top: 8px; margin-bottom: 22px;
        display: grid; grid-template-columns: 220px 1fr; gap: 28px; align-items: center;
    }
    .gauge { text-align: center; }
    .gauge svg { width: 100%; max-width: 220px; height: auto; display:block; margin: 0 auto; }
    .gauge .num { font-family:'Barlow Semi Condensed',sans-serif; font-size: 2.6rem; font-weight: 700; fill: #0F172A !important; }
    .gauge .of  { font-size: 0.8rem; fill: #1E293B !important; font-weight: 600; }
    .verdict .label { font-family:'Barlow Semi Condensed',sans-serif; font-size: 1.6rem; font-weight: 700; margin-bottom: 4px; }
    .verdict .desc { color: #1E293B !important; line-height: 1.55; margin-bottom: 14px; font-weight: 500; }
    .chips { display:flex; flex-wrap:wrap; gap:6px; margin-top: 6px; }
    .chips-title { font-size: 0.8rem; color: #1E293B !important; margin-top: 10px; font-weight: 700; }
    .chip { border-radius: 6px; padding: 4px 10px; font-size: 0.82rem; font-weight: 600; border: 1px solid; }
    .chip.ok   { color:#047857 !important; background:#ECFDF5; border-color:#A7F3D0; }
    .chip.miss { color:#B45309 !important; background:#FEF3C7; border-color:#FDE68A; }

    .model-answer {
        background: #F8FAFC; color: #0F172A !important; border-radius: 12px;
        padding: 22px 28px; margin-bottom: 22px; border-left: 5px solid var(--green);
    }
    .model-answer .h { font-family:'Barlow Semi Condensed',sans-serif; font-weight:700; font-size:1.05rem; color: var(--green) !important; margin-bottom: 8px; }
    .model-answer .t { line-height: 1.7; font-size: 1rem; max-width: 100%; color: #0F172A !important; font-weight: 500; }

    /* ---------- Tip ---------- */
    .tip {
        background: #F8FAFC; border: 1px dashed #CBD5E1; border-radius: 12px;
        padding: 16px 22px; color: #1E293B !important; font-size: 0.92rem; line-height: 1.6; font-weight: 500;
    }
    .tip b { color: #0F172A !important; font-weight: 700; }

    /* ---------- Flight progress ---------- */
    .flight {
        background: var(--card); border: 1px solid var(--line); border-radius: 12px; padding: 22px 24px;
    }
    .flight .h { font-family:'Barlow Semi Condensed',sans-serif; font-weight:700; font-size:1.1rem; color: #0F172A !important; margin-bottom: 14px; }
    .flight .pct { font-family:'Barlow Semi Condensed',sans-serif; font-size: 2.6rem; font-weight: 700; color: #0F172A !important; line-height: 1; font-variant-numeric: tabular-nums; }
    .flight .track { position: relative; height: 4px; background: #E2E8F0; border-radius: 4px; margin: 22px 8px 10px 8px; }
    .flight .fill  { position:absolute; left:0; top:0; bottom:0; background: var(--amber); border-radius: 4px; }
    .flight .dot   { position:absolute; top:50%; width: 16px; height: 16px; border-radius: 50%; background: #FFFFFF; border: 3px solid var(--amber); transform: translate(-50%, -50%); }
    .flight .end   { position:absolute; right:-8px; top:50%; width: 10px; height: 10px; background: #0F172A; transform: translateY(-50%) rotate(45deg); }
    .flight .legend { display:flex; justify-content:space-between; color: #1E293B !important; font-size: 0.8rem; margin: 0 4px; font-weight: 600; }
    .flight .note { margin-top: 14px; color: #1E293B !important; font-size: 0.9rem; line-height: 1.5; font-weight: 500; }
    .flight .note b { color: #0F172A !important; font-weight: 700; }

    /* Radar styling */
    .radar {
        position: relative; width: 112px; height: 112px; margin: 26px auto 8px auto; border-radius: 50%;
        background:
            radial-gradient(circle, transparent 0 24%, rgba(15,23,42,.18) 24.5% 25.5%, transparent 26% 49%, rgba(15,23,42,.18) 49.5% 50.5%, transparent 51% 74%, rgba(15,23,42,.18) 74.5% 75.5%, transparent 76%),
            linear-gradient(90deg, transparent 49.5%, rgba(15,23,42,.15) 49.5% 50.5%, transparent 50.5%),
            linear-gradient(0deg, transparent 49.5%, rgba(15,23,42,.15) 49.5% 50.5%, transparent 50.5%),
            #F1F5F9;
        border: 1px solid #CBD5E1;
        overflow: hidden;
    }
    .radar::before {
        content: ''; position: absolute; inset: 0; border-radius: 50%;
        background: conic-gradient(from 0deg, rgba(5,150,105,0) 0deg, rgba(5,150,105,0) 290deg, rgba(5,150,105,.35) 360deg);
        animation: sweep 7s linear infinite;
    }
    .radar .blip {
        position: absolute; width: 5px; height: 5px; border-radius: 50%; background: var(--green);
        box-shadow: 0 0 6px var(--green); opacity: .15; animation: blip 7s linear infinite;
    }
    .radar .blip.b1 { top: 28%; left: 64%; animation-delay: 1.1s; }
    .radar .blip.b2 { top: 66%; left: 34%; animation-delay: 4.4s; }
    @keyframes sweep { to { transform: rotate(360deg); } }
    @keyframes blip { 0%, 100% { opacity: .15; } 8% { opacity: 1; } 45% { opacity: .15; } }

    /* ---------- Login hero ---------- */
    .login-hero {
        min-height: 245px;
        padding: 30px 34px 26px !important;
        margin-bottom: 24px;
        background: linear-gradient(125deg, #F8FAFC 0%, #F1F5F9 100%) !important;
        border: 1px solid #CBD5E1 !important;
        border-radius: 28px !important;
        color: #0F172A !important;
        box-shadow: 0 10px 30px rgba(0,0,0,.04) !important;
    }
    .login-hero .title { color:#0F172A !important; font-size:clamp(2rem,4vw,3.2rem) !important; }
    .login-hero .sub { color:#1E293B !important; font-weight: 500; }
    .login-kicker { color:#2563EB !important; font-size:11px; font-weight:800; letter-spacing:.14em; }
    .login-widget b { display:block;font-size:12px;color:#0F172A !important;font-weight:800; }
    .login-widget small { display:block;font-size:10px;color:#1E293B !important;margin-top:2px;font-weight:500; }
    div[data-testid="stTextInput"] label, div[data-testid="stTextInput"] label p { color:#0F172A !important;font-size:13px !important;font-weight:800 !important; }
    div[data-testid="stTextInput"] input {
        background:#FFFFFF !important;color:#0F172A !important;
        -webkit-text-fill-color:#0F172A !important;
        border:1.5px solid #CBD5E1 !important;border-radius:14px !important;
        font-weight: 600 !important;
    }

    .st-key-mic_card {
        background: #FFFFFF !important;
        border: 1px solid #E2E8F0 !important;
        border-radius: 20px !important;
        padding: 12px 16px 10px !important;
    }
    .stTextArea textarea {
        height: 92px !important; min-height: 92px !important; padding: 10px 12px !important;
        background: #FFFFFF !important; color: #0F172A !important; font-weight: 500 !important;
    }

    div[data-testid="stButton"] button {
        min-height: 48px !important;
        height: 48px !important;
        padding: 0.6rem 1rem !important;
        font-size: 1rem !important;
        font-weight: 700 !important;
    }
</style>
""", unsafe_allow_html=True)

ALL_CATEGORIES = "All Categories"

# Helper functions
def normalize_text(text: str) -> str:
    """Lowercase text for English matching (standard Unicode casing)."""
    if not text:
        return ""
    return text.lower()

def transcribe_audio(audio_bytes):
    recognizer = sr.Recognizer()
    try:
        audio_file = io.BytesIO(audio_bytes)
        with sr.AudioFile(audio_file) as source:
            audio_data = recognizer.record(source)
            return recognizer.recognize_google(audio_data, language="en-US")
    except Exception:
        return ""

def is_flexible_match(keyword: str, clean_answer: str) -> bool:
    clean_kw = normalize_text(str(keyword).strip())
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
    clean_answer = re.sub(r'[^\w\s]', ' ', normalize_text(user_answer))
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

# Session state initialization
if "user" not in st.session_state: st.session_state.user = None
if "session" not in st.session_state: st.session_state.session = None
if "sorulan_ids" not in st.session_state: st.session_state.sorulan_ids = []
if "puanlar" not in st.session_state: st.session_state.puanlar = []
if "mevcut_soru" not in st.session_state: st.session_state.mevcut_soru = None
if "son_analiz" not in st.session_state: st.session_state.son_analiz = None
if "secilen_kategori" not in st.session_state: st.session_state.secilen_kategori = ALL_CATEGORIES
if "last_processed_audio" not in st.session_state: st.session_state.last_processed_audio = None

# SUPABASE CHECK AND SESSION RESTORE
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

# --- VISUAL HELPERS (UI only) ---
SKOR_BILGI = {
    100: ("Excellent", "#059669", "Your answer fully matches the expected response. Keep up this level."),
    80:  ("Very Good", "#059669", "Your answer is largely sufficient. Add the missing concepts to reach 100."),
    60:  ("Moderate", "#D97706", "The core idea is there, but some important details are missing."),
    30:  ("Needs Work", "#DC2626", "Your answer is far from the correct one. Read the sample answer and try again."),
    0:   ("Inadequate", "#DC2626", "The targeted explanations were not found in your answer."),
}

def gauge_svg(puan: int, renk: str) -> str:
    uzunluk = 251.33
    dolu = uzunluk * (puan / 100)
    return f"""
    <svg viewBox="0 0 200 124" role="img" aria-label="Score {puan} / 100">
        <path d="M20 104 A80 80 0 0 1 180 104" fill="none" stroke="#E2E8F0" stroke-width="14" stroke-linecap="round"/>
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

# --- LOGIN / SIGN-UP SCREEN ---
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
        <div class="sub">Prepare for your airline interview with technical questions. Your progress is saved to your account.</div>
        <div class="login-widgets">
            <div class="login-widget"><span class="widget-icon">◉</span><span><b>Live practice</b><small>Answer by speaking</small></span><i class="widget-pulse"></i></div>
            <div class="login-widget"><span class="widget-icon">⌁</span><span><b>Flight instruments</b><small>Track your progress</small></span><span class="mini-bars"><i></i><i></i><i></i><i></i><i></i></span></div>
            <div class="login-widget"><span class="widget-icon">✦</span><span><b>Smart evaluation</b><small>Feedback on your answer</small></span><span class="widget-check">✓</span></div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    col_auth1, col_auth2, col_auth3 = st.columns([1, 1.7, 1])
    with col_auth2:
        tab_login, tab_signup = st.tabs(["Log in", "Sign up"])

        with tab_login:
            login_email = st.text_input("Email", key="l_email")
            login_pass = st.text_input("Password", type="password", key="l_pass")
            if st.button("Log in", type="primary", use_container_width=True):
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
                    st.error("Supabase connection details are missing (Secrets).")

        with tab_signup:
            signup_email = st.text_input("Email", key="s_email")
            signup_pass = st.text_input("Password (at least 6 characters)", type="password", key="s_pass")
            if st.button("Create account", use_container_width=True):
                if supabase:
                    try:
                        res = supabase.auth.sign_up({"email": signup_email, "password": signup_pass})
                        st.session_state.user = res.user
                        st.session_state.session = res.session
                        save_user_progress()
                        st.success("Your account has been created!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Sign-up error: {e}")
    st.stop()

# If logged in, load progress (on first load)
if st.session_state.user and not st.session_state.sorulan_ids and not st.session_state.puanlar:
    load_user_progress()

# --- APPLICATION FLOW AFTER LOGIN ---

def yeni_soru_getir(kategori_filtresi):
    if kategori_filtresi == ALL_CATEGORIES:
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

# Calculations
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

kategoriler = [ALL_CATEGORIES] + sorted(list(set(q["category"] for q in questions_data))) if questions_data else []

def on_kategori_change():
    yeni_kat = st.session_state.kat_select_box
    st.session_state.secilen_kategori = yeni_kat
    yeni_soru_getir(yeni_kat)

kat_index = kategoriler.index(st.session_state.secilen_kategori) if st.session_state.secilen_kategori in kategoriler else 0

secilen_kategori = st.sidebar.selectbox("Interview category", kategoriler, index=kat_index, key="kat_select_box", on_change=on_kategori_change)

st.sidebar.markdown(f"""
<div style="margin-top:14px;">
    <div class="side-stat"><span>Answered</span><b>{tamamlanan}</b></div>
    <div class="side-stat"><span>Average score</span><b>{ort_skor:.0f}%</b></div>
    <div class="side-stat"><span>Target</span><b>80%+</b></div>
</div>
""", unsafe_allow_html=True)

st.sidebar.markdown("<div style='height:18px'></div>", unsafe_allow_html=True)

if st.sidebar.button("Reset progress", use_container_width=True, help="Resets all your answer and score history."):
    reset_user_progress()
    st.rerun()

st.sidebar.markdown("""
<div class="radar"><span class="blip b1"></span><span class="blip b2"></span></div>
""", unsafe_allow_html=True)

if st.sidebar.button("Sign out", use_container_width=True):
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

# User display name
def display_name(email: str) -> str:
    local = (email or "").split("@")[0]
    words = [w for w in re.split(r"[._\-\s]+", local) if w]
    out = [w[0].upper() + normalize_text(w[1:]) for w in words]
    return " ".join(out) if out else "Pilot Candidate"

kullanici_adi = display_name(st.session_state.user.email)
avatar_harf = html.escape(kullanici_adi[0])
kullanici_adi_html = html.escape(kullanici_adi)

# Hero banner
st.markdown(f"""
<div class="hero">
    <div class="cloud c1"></div><div class="cloud c2"></div>
    <div class="plane"><svg viewBox="0 0 120 44" aria-hidden="true"><path fill="#0F172A" d="M4 24 Q4 19 14 19 L92 19 Q113 20 117 24 Q113 28 92 29 L14 29 Q4 29 4 24Z"/><path fill="#0F172A" d="M12 19 L3 5 L16 5 L30 19Z"/><path fill="#0F172A" d="M50 27 L72 41 L84 41 L70 27Z"/><path fill="#0F172A" opacity=".7" d="M52 20 L70 9 L80 9 L68 20Z"/><circle cx="100" cy="23.5" r="1.6" fill="#FFFFFF"/><circle cx="92" cy="23.5" r="1.6" fill="#FFFFFF"/><circle cx="84" cy="23.5" r="1.6" fill="#FFFFFF"/></svg></div>
    <div class="welcome">
        <div class="avatar">{avatar_harf}</div>
        <div>
            <div class="hi">Welcome</div>
            <div class="name">{kullanici_adi_html}</div>
        </div>
    </div>
    <div class="title">Prepare for your pilot interview</div>
    <div class="sub">Answer technical questions by voice and use aviation terminology clearly. Your progress is saved to your account automatically.</div>
</div>
""", unsafe_allow_html=True)

# Instrument strip
st.markdown(f"""
<div class="strip">
    <div class="cell"><div class="k">Total questions</div><div class="v">{toplam_soru}</div></div>
    <div class="cell"><div class="k">Categories</div><div class="v">{max(len(kategoriler)-1, 0)}</div></div>
    <div class="cell"><div class="k">Average score</div><div class="v">{ort_skor:.0f}%</div></div>
    <div class="cell"><div class="k">Target score</div><div class="v">80%<small>and above</small></div></div>
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
            model_answer_text = "Key topic expected to be covered in the interview for this question: a correct and precise explanation of the following concepts: " + ", ".join(kw_list) + "."

        with st.container(key="mic_card"):
            st.markdown("""
            <div class="mic-h">Voice answer</div>
            <div class="mic-s">Turn on the microphone and speak. Your words are transcribed to text in real time; no audio file is saved.</div>
            """, unsafe_allow_html=True)
            live_text = live_speech_input(
                key=f"live_{soru.get('id')}_{len(st.session_state.sorulan_ids)}",
                default=""
            )
            if isinstance(live_text, str) and live_text.strip():
                st.session_state[input_key] = live_text

        kullanici_cevabi = st.text_area("Detected / typed answer", placeholder="Text appears here as you speak into the microphone. You can also edit it manually.", height=130, key=input_key)

        btn_c1, btn_c2 = st.columns([1, 1])
        with btn_c1:
            if st.button("Evaluate answer", type="primary", use_container_width=True):
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
                    st.warning("Please speak or type an answer first.")

        with btn_c2:
            if st.button("Next question", use_container_width=True):
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
                kw_html += f'<div class="chips-title">Concepts found in your answer</div><div class="chips">{chips_html(matched, "ok")}</div>'
            if missing:
                kw_html += f'<div class="chips-title">Concepts you could add</div><div class="chips">{chips_html(missing, "miss")}</div>'

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
                <div class="h">Expected sample answer in the interview</div>
                <div class="t">{model_answer_html}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("""
    <div class="tip">
        <b>Interview tip:</b> When explaining how systems work, emphasizing <b>cause-and-effect relationships</b> and standard operating procedures (SOPs) will improve your score.
    </div>
    """, unsafe_allow_html=True)

with col_right:
    yuzde = min(int((tamamlanan / toplam_soru) * 100), 100) if toplam_soru > 0 else 0
    st.markdown(f"""
    <div class="flight">
        <div class="h">Flight progress</div>
        <div class="pct">{yuzde}%</div>
        <div class="track">
            <div class="fill" style="width:{yuzde}%;"></div>
            <div class="dot" style="left:{yuzde}%;"></div>
            <div class="end"></div>
        </div>
        <div class="legend"><span>Departure</span><span>Arrival</span></div>
        <div class="note">You have answered <b>{tamamlanan}</b> of <b>{toplam_soru}</b> questions.</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)
    components.html("""
    <html><head><style>
      @import url('https://fonts.googleapis.com/css2?family=Barlow+Semi+Condensed:wght@500;600;700&display=swap');
      html,body{margin:0;background:transparent;font-family:'Barlow Semi Condensed',sans-serif;}
      .card{background:#FFFFFF;border:1px solid #E2E8F0;border-radius:12px;padding:16px 18px;color:#0F172A;display:flex;align-items:center;gap:18px;flex-wrap:wrap;box-sizing:border-box;box-shadow:0 4px 16px rgba(0,0,0,.03);}
      .adi{width:104px;height:104px;flex-shrink:0;}
      .horizon{transform-origin:60px 60px;animation:bank 11s ease-in-out infinite alternate;}
      @keyframes bank{from{transform:rotate(-4deg) translateY(-3px);}to{transform:rotate(5deg) translateY(4px);}}
      .clk{min-width:120px;}
      .row{margin-bottom:8px;}
      .lab{color:#0F172A;font-size:12px;font-weight:700;}
      .t{font-size:26px;font-weight:700;line-height:1.05;font-variant-numeric:tabular-nums;color:#0F172A;}
      .t.utc{color:#D97706;}
      @media (prefers-reduced-motion: reduce){.horizon{animation:none;}}
    </style></head><body>
    <div class="card">
      <svg class="adi" viewBox="0 0 120 120" aria-hidden="true">
        <defs><clipPath id="c"><circle cx="60" cy="60" r="52"/></clipPath></defs>
        <g clip-path="url(#c)"><g class="horizon">
          <rect x="-60" y="-60" width="240" height="120" fill="#38BDF8"/>
          <rect x="-60" y="60" width="240" height="120" fill="#A16207"/>
          <line x1="-60" y1="60" x2="180" y2="60" stroke="#fff" stroke-width="1.5"/>
          <line x1="46" y1="48" x2="74" y2="48" stroke="#fff" stroke-width="1" opacity=".7"/>
          <line x1="52" y1="36" x2="68" y2="36" stroke="#fff" stroke-width="1" opacity=".7"/>
          <line x1="46" y1="72" x2="74" y2="72" stroke="#fff" stroke-width="1" opacity=".7"/>
          <line x1="52" y1="84" x2="68" y2="84" stroke="#fff" stroke-width="1" opacity=".7"/>
        </g></g>
        <circle cx="60" cy="60" r="52" fill="none" stroke="#CBD5E1" stroke-width="5"/>
        <path d="M60 4 L56 12 L64 12Z" fill="#D97706"/>
        <path d="M28 62 H48 L52 66 M92 62 H72 L68 66" fill="none" stroke="#D97706" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round"/>
        <circle cx="60" cy="62" r="3" fill="#D97706"/>
      </svg>
      <div class="clk">
        <div class="row"><div class="lab">UTC (Zulu)</div><div class="t utc" id="u">--:--:--</div></div>
        <div class="row" style="margin-bottom:0"><div class="lab">Local time (Türkiye)</div><div class="t" id="l">--:--:--</div></div>
      </div>
    </div>
    <script>
      function tick(){
        var d=new Date();
        document.getElementById('u').textContent=d.toLocaleTimeString('en-GB',{timeZone:'UTC',hour12:false});
        document.getElementById('l').textContent=d.toLocaleTimeString('en-GB',{timeZone:'Europe/Istanbul',hour12:false});
      }
      tick(); setInterval(tick,1000);
    </script></body></html>
    """, height=140)
