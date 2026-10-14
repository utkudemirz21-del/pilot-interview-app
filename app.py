import json
import base64
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

    /* ---------- Sidebar (cockpit panel) ---------- */
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

    /* ---------- Instrument strip (summary metrics) ---------- */
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
    .tag-cat { background: var(--panel); color:#fff; border-radius: 6px; padding: 5px 12px; font-size: 0.82rem; font-weight: 500; }
    .tag-diff { border-radius: 6px; padding: 5px 12px; font-size: 0.82rem; font-weight: 600; border: 1px solid; }
    .tag-diff.easy   { color:#13795B; border-color:#9ADBC4; background:#EAF8F2; }
    .tag-diff.medium { color:#8A5B00; border-color:#F2D18A; background:#FEF6E1; }
    .tag-diff.hard   { color:#A82F28; border-color:#EFB1AC; background:#FDEEEC; }
    .q-text { font-family:'Barlow Semi Condensed',sans-serif; font-size: 2.1rem !important; font-weight: 700 !important; color: var(--ink); line-height: 1.35; max-width: 100%; }

    /* ---------- Microphone panel ---------- */
    .st-key-mic_card {
        background: var(--card);
        border: 1px solid var(--line);
        border-radius: 12px;
        padding: 18px 22px 8px 22px;
        margin-bottom: 18px;
    }
    .mic-h { font-family:'Barlow Semi Condensed',sans-serif; font-weight:600; font-size:1.15rem; color:var(--ink); }
    .mic-s { color: var(--ink-soft); font-size: 0.88rem; margin: 2px 0 10px 0; }

    /* ---------- Form elements ---------- */
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

    /* ---------- Report card (score gauge) ---------- */
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

    /* ---------- Tip ---------- */
    .tip {
        background: transparent; border: 1px dashed #B5C0CF; border-radius: 12px;
        padding: 16px 22px; color: var(--ink-soft); font-size: 0.92rem; line-height: 1.6;
    }
    .tip b { color: var(--ink); }

    /* ---------- Flight progress ---------- */
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

    /* ---------- Premium polish ---------- */
    .block-container { padding-bottom: 3rem; }
    section[data-testid="stSidebar"] [data-testid="stSidebarContent"] { padding-top: 1.35rem; }
    .hero {
        box-shadow: 0 18px 44px rgba(10,22,38,.12);
        border: 1px solid rgba(255,255,255,.08);
    }
    .hero .title { letter-spacing: -.4px; }
    .strip {
        box-shadow: 0 8px 24px rgba(14,26,43,.035);
    }
    .strip .cell { transition: background .2s ease; }
    .strip .cell:hover { background: #F8FAFC; }
    .brief {
        box-shadow: 0 10px 28px rgba(14,26,43,.045);
        transition: box-shadow .2s ease, transform .2s ease;
    }
    .brief:hover { box-shadow: 0 14px 32px rgba(14,26,43,.075); }
    .tag-cat { letter-spacing: .2px; }
    .q-text { overflow-wrap: anywhere; }
    .st-key-mic_card {
        box-shadow: 0 10px 28px rgba(14,26,43,.045);
        transition: border-color .2s ease, box-shadow .2s ease;
    }
    .st-key-mic_card:focus-within {
        border-color: rgba(60,125,217,.6);
        box-shadow: 0 0 0 3px rgba(60,125,217,.09), 0 10px 28px rgba(14,26,43,.045);
    }
    .st-key-mic_card button {
        border-radius: 14px !important;
        box-shadow: 0 6px 18px rgba(10,22,38,.12);
        transition: transform .18s ease, box-shadow .18s ease, filter .18s ease;
    }
    .st-key-mic_card button:hover {
        transform: translateY(-1px);
        box-shadow: 0 10px 24px rgba(10,22,38,.18);
        filter: brightness(1.08);
    }
    .report {
        position: relative;
        overflow: hidden;
        box-shadow: 0 12px 32px rgba(14,26,43,.055);
    }
    .report::before {
        content: "FLIGHT PERFORMANCE";
        position: absolute; top: 0; right: 0;
        padding: 7px 12px;
        border-bottom-left-radius: 8px;
        background: #F3F6FA;
        color: #6B7B90;
        font-size: .65rem;
        font-weight: 700;
        letter-spacing: 1.1px;
    }
    .gauge { padding-top: 8px; }
    .verdict .label { letter-spacing: -.2px; }
    .chip { overflow-wrap: anywhere; }
    .model-answer {
        box-shadow: 0 12px 30px rgba(10,22,38,.10);
        overflow-wrap: anywhere;
    }
    .model-answer .t { white-space: pre-wrap; }
    .flight {
        box-shadow: 0 10px 28px rgba(14,26,43,.045);
        overflow: hidden;
    }
    .tip { background: rgba(255,255,255,.45); }
    div[data-testid="stAlert"] { border-radius: 10px; }

    /* ---------- Motion ---------- */
    .hero .plane {
        position: absolute; z-index: 0; left: -160px; top: 64%;
        width: 92px; opacity: .5; pointer-events: none;
        transform: rotate(-5deg);
        animation: planeFly 46s linear 3s infinite;
    }
    .hero .plane svg { width: 100%; height: auto; display: block; }
    .hero .plane::before {
        content: ''; position: absolute; right: 88%; top: 50%; height: 2px; width: 190px;
        background: linear-gradient(90deg, rgba(255,255,255,0), rgba(255,255,255,.4));
        border-radius: 2px;
    }
    @keyframes planeFly {
        0%   { left: -160px; top: 66%; }
        100% { left: 104%;  top: 14%; }
    }
    .hero .cloud {
        position: absolute; z-index: 0; border-radius: 50%; pointer-events: none;
        background: radial-gradient(closest-side, rgba(255,255,255,.10), rgba(255,255,255,0));
        filter: blur(6px);
    }
    .hero .cloud.c1 { width: 340px; height: 70px; top: 18%; left: -360px; animation: cloudDrift 120s linear infinite; }
    .hero .cloud.c2 { width: 260px; height: 54px; top: 52%; left: -300px; animation: cloudDrift 160s linear 25s infinite; opacity: .8; }
    @keyframes cloudDrift { to { left: 105%; } }

    .brief { animation: softIn .45s ease-out both; }
    .report, .model-answer { animation: softIn .5s ease-out both; }
    @keyframes softIn { from { opacity: 0; transform: translateY(6px); } to { opacity: 1; transform: none; } }

    .gauge .arc { animation: gaugeFill 1.1s cubic-bezier(.2,.8,.2,1) both; }
    @keyframes gaugeFill { from { stroke-dasharray: 0 251.33; } }

    .flight .fill { animation: growX 1s cubic-bezier(.2,.8,.2,1) both; transform-origin: left; }
    @keyframes growX { from { transform: scaleX(0); } }
    .flight .dot::after {
        content: ''; position: absolute; inset: -7px; border-radius: 50%;
        border: 2px solid var(--amber); opacity: 0;
        animation: ping 3s ease-out infinite;
    }
    @keyframes ping { 0% { transform: scale(.6); opacity: .7; } 70%, 100% { transform: scale(1.5); opacity: 0; } }

    .radar {
        position: relative; width: 112px; height: 112px; margin: 26px auto 8px auto; border-radius: 50%;
        background:
            radial-gradient(circle, transparent 0 24%, rgba(143,168,200,.22) 24.5% 25.5%, transparent 26% 49%, rgba(143,168,200,.22) 49.5% 50.5%, transparent 51% 74%, rgba(143,168,200,.22) 74.5% 75.5%, transparent 76%),
            linear-gradient(90deg, transparent 49.5%, rgba(143,168,200,.18) 49.5% 50.5%, transparent 50.5%),
            linear-gradient(0deg, transparent 49.5%, rgba(143,168,200,.18) 49.5% 50.5%, transparent 50.5%),
            #0D1D33;
        border: 1px solid var(--panel-line);
        overflow: hidden;
    }
    .radar::before {
        content: ''; position: absolute; inset: 0; border-radius: 50%;
        background: conic-gradient(from 0deg, rgba(47,191,143,0) 0deg, rgba(47,191,143,0) 290deg, rgba(47,191,143,.38) 360deg);
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

    /* ---------- Premium dark cockpit ---------- */
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
    section[data-testid="stSidebar"] [data-testid="stSelectbox"] div[data-baseweb="select"] > div {
        background: #0B203B !important; border: 1px solid #254A75 !important;
        border-radius: 14px !important; color: #EAF2FF !important;
    }
    section[data-testid="stSidebar"] .side-stat {
        border-bottom-color: #1B3A61 !important;
    }
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
    .hero::after {
        content: ""; position: absolute; inset: 0; pointer-events: none;
        background: repeating-linear-gradient(90deg, transparent 0 43px, rgba(110,165,226,.045) 44px 45px);
    }
    .hero .title { color: #F4F8FF !important; }
    .hero .title span, .hero .accent { color: var(--amber) !important; }
    .hero .sub, .hero .hi { color: #AFC5E3 !important; }
    .strip {
        background: linear-gradient(145deg, rgba(13,35,62,.96), rgba(7,23,43,.96)) !important;
        border: 1px solid #24486F !important; border-radius: 22px !important;
        box-shadow: 0 12px 30px rgba(0,0,0,.18), inset 0 1px rgba(255,255,255,.035);
    }
    .strip .cell { border-right-color: #24415F !important; }
    .strip .k { color: #9DB5D5 !important; }
    .strip .v { color: #F0F6FF !important; }
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
    .mic-s, .strip .k, .flight .legend, .flight .note, .verdict .desc,
    .chips-title, .tip { color: #9DB5D5 !important; }
    .tag-cat { background: #17365E !important; border: 1px solid #315A88; border-radius: 999px !important; }
    .tag-diff { border-radius: 999px !important; }
    .tag-diff.easy { color: #65E7C1 !important; border-color: #226C65 !important; background: #0C393B !important; }
    .tag-diff.medium { color: #FFD16A !important; border-color: #745B29 !important; background: #3A2D17 !important; }
    .tag-diff.hard { color: #FF9DA6 !important; border-color: #783D4A !important; background: #3A1E2B !important; }
    .stTextArea textarea, .stTextInput input {
        background: #06172D !important; color: #EAF2FF !important;
        border: 1px solid #254A75 !important; border-radius: 17px !important;
    }
    .stTextArea textarea::placeholder, .stTextInput input::placeholder { color: #7894B9 !important; }
    .stTextArea textarea:focus, .stTextInput input:focus {
        border-color: #35BDF5 !important; box-shadow: 0 0 0 3px rgba(53,189,245,.13) !important;
    }
    .stButton button {
        border-radius: 16px !important; min-height: 44px;
        transition: transform .18s ease, box-shadow .18s ease, border-color .18s ease;
    }
    .stButton button[kind="primary"], .stButton button[data-testid="stBaseButton-primary"] {
        background: linear-gradient(135deg, #FFC34F, #F4A91D) !important;
        color: #07162B !important; border: 1px solid #FFC34F !important;
        box-shadow: 0 7px 20px rgba(255,181,46,.16);
    }
    .stButton button[kind="secondary"], .stButton button[data-testid="stBaseButton-secondary"] {
        background: #0C2340 !important; color: #DDEBFF !important;
        border: 1px solid #2B507A !important;
    }
    .stButton button:hover { transform: translateY(-1px); box-shadow: 0 10px 24px rgba(0,0,0,.24); }
    .st-key-mic_card { padding: 22px 24px 18px !important; }
    .st-key-mic_card button {
        min-width: 118px !important; min-height: 118px !important;
        border-radius: 50% !important;
        background: radial-gradient(circle at 35% 25%, #4B9BFF 0%, #2168C8 48%, #0A2D69 100%) !important;
        border: 3px solid #74CFFF !important;
        box-shadow: 0 0 0 8px rgba(53,189,245,.10), 0 0 34px rgba(40,126,255,.38), inset 0 2px 10px rgba(255,255,255,.22) !important;
        color: white !important;
    }
    .st-key-mic_card button:hover {
        transform: scale(1.035) !important;
        box-shadow: 0 0 0 10px rgba(53,189,245,.13), 0 0 42px rgba(40,126,255,.52) !important;
    }
    .flight .track { background: #1B3A61 !important; height: 7px !important; border-radius: 99px !important; }
    .flight .fill { background: linear-gradient(90deg, #2A8DFF, #44D8F0) !important; border-radius: 99px !important; }
    .flight .dot { background: #07172C !important; border-color: #FFB52E !important; }
    .flight .end { background: #D9E8FF !important; }
    .report::before { background: #102A49 !important; color: #9BB5D7 !important; }
    .gauge .num { fill: #F0F6FF !important; }
    .gauge .of { fill: #9BB5D7 !important; }
    .tip { border: 1px solid #24486F !important; }
    div[data-testid="stAlert"] { border-radius: 16px !important; }
    div[data-testid="stSpinner"] * { color: #DDEBFF !important; }

    /* Category selector */
    section[data-testid="stSidebar"] [data-testid="stSelectbox"] label,
    section[data-testid="stSidebar"] [data-testid="stSelectbox"] label p {
        color: #F1F6FF !important;
        font-weight: 800 !important;
        letter-spacing: .01em;
    }
    section[data-testid="stSidebar"] [data-testid="stSelectbox"] div[data-baseweb="select"] > div {
        background: #FFFFFF !important;
        border: 1px solid #D5DFED !important;
        border-radius: 12px !important;
        color: #13243B !important;
        box-shadow: 0 4px 12px rgba(0,0,0,.12) !important;
    }
    section[data-testid="stSidebar"] [data-testid="stSelectbox"] div[data-baseweb="select"] span,
    section[data-testid="stSidebar"] [data-testid="stSelectbox"] div[data-baseweb="select"] input {
        color: #13243B !important;
        -webkit-text-fill-color: #13243B !important;
        font-weight: 650 !important;
    }
    div[data-baseweb="popover"] ul,
    div[data-baseweb="popover"] li,
    div[data-baseweb="menu"] li {
        background: #FFFFFF !important;
        color: #13243B !important;
        font-weight: 700 !important;
    }
    div[data-baseweb="popover"] li:hover,
    div[data-baseweb="menu"] li:hover {
        background: #EAF2FC !important;
    }
    .brief .q-text, .q-text, .mic-h, .flight .h,
    .chips-title, .verdict .label,
    [data-testid="stMarkdownContainer"] h1,
    [data-testid="stMarkdownContainer"] h2,
    [data-testid="stMarkdownContainer"] h3 {
        color: #F3F7FF !important;
        font-weight: 800 !important;
        letter-spacing: -.015em;
    }
    .st-key-mic_card button,
    .st-key-mic_card [data-testid="stBaseButton-secondary"],
    .st-key-mic_card [data-testid="stBaseButton-primary"],
    button[aria-label*="Mic"],
    button[title*="Mic"] {
        width: 116px !important;
        height: 116px !important;
        min-width: 116px !important;
        min-height: 116px !important;
        padding: 0 !important;
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;
        border-radius: 50% !important;
        background: radial-gradient(circle at 32% 24%, #63B8FF 0%, #287CE1 42%, #0B347B 100%) !important;
        border: 3px solid #8AE0FF !important;
        color: #FFFFFF !important;
        box-shadow: 0 0 0 7px rgba(53,189,245,.12),
                    0 0 28px rgba(41,132,255,.42),
                    inset 0 2px 10px rgba(255,255,255,.25) !important;
        transition: transform .18s ease, box-shadow .18s ease !important;
    }
    .st-key-mic_card button p,
    .st-key-mic_card button span,
    .st-key-mic_card button svg,
    button[aria-label*="Mic"] svg,
    button[title*="Mic"] svg {
        color: #FFFFFF !important;
        fill: currentColor !important;
        stroke: currentColor !important;
    }
    .st-key-mic_card button:hover,
    button[aria-label*="Mic"]:hover,
    button[title*="Mic"]:hover {
        transform: scale(1.045) !important;
        box-shadow: 0 0 0 10px rgba(53,189,245,.15),
                    0 0 42px rgba(41,132,255,.60),
                    inset 0 2px 10px rgba(255,255,255,.28) !important;
    }
    .st-key-mic_card button:focus-visible {
        outline: 3px solid #FFB52E !important;
        outline-offset: 6px !important;
    }

    section[data-testid="stSidebar"] [data-testid="stSelectbox"] label,
    section[data-testid="stSidebar"] [data-testid="stSelectbox"] label p {
        color: #F3F7FF !important;
        font-weight: 800 !important;
    }
    section[data-testid="stSidebar"] [data-testid="stSelectbox"] [role="combobox"],
    section[data-testid="stSidebar"] [data-testid="stSelectbox"] [role="combobox"] * {
        background-color: #FFFFFF !important;
        color: #14243A !important;
        -webkit-text-fill-color: #14243A !important;
        font-weight: 700 !important;
        opacity: 1 !important;
    }
    section[data-testid="stSidebar"] [data-testid="stSelectbox"] [role="combobox"] {
        border: 1px solid #D5DFED !important;
        border-radius: 12px !important;
    }
    div[data-baseweb="popover"] [role="option"],
    div[data-baseweb="popover"] [role="option"] * {
        color: #14243A !important;
        -webkit-text-fill-color: #14243A !important;
        font-weight: 700 !important;
    }
    div[data-baseweb="popover"] [role="option"]:hover {
        background: #EAF2FC !important;
    }

    .st-key-mic_card [data-testid="stAudioInput"],
    .st-key-mic_card [data-testid="stAudioInput"] > div {
        background: #071A31 !important;
        color: #EAF2FF !important;
        border-radius: 18px !important;
    }
    .st-key-mic_card [data-testid="stAudioInput"] button {
        width: 58px !important;
        height: 58px !important;
        min-width: 58px !important;
        min-height: 58px !important;
        border-radius: 50% !important;
        background: linear-gradient(145deg, #4BA8FF, #1554B5) !important;
        color: #FFFFFF !important;
        border: 2px solid #83DFFF !important;
        box-shadow: 0 0 0 5px rgba(53,189,245,.12), 0 0 25px rgba(41,132,255,.35) !important;
    }
    .st-key-mic_card [data-testid="stAudioInput"] button svg {
        color: #FFFFFF !important;
        fill: currentColor !important;
    }
    .st-key-mic_card [data-testid="stAudioInput"] button:hover {
        transform: scale(1.04) !important;
        box-shadow: 0 0 0 8px rgba(53,189,245,.15), 0 0 34px rgba(41,132,255,.5) !important;
    }

/* ---------- Login hero ---------- */
.login-hero {
    min-height: 245px;
    padding: 30px 34px 26px !important;
    margin-bottom: 24px;
    background:
      radial-gradient(ellipse at 78% 0%, rgba(73,132,183,.13), transparent 42%),
      linear-gradient(135deg, #172B41 0%, #13253A 55%, #102033 100%) !important;
    border: 1px solid #2D4763 !important;
    border-radius: 22px !important;
    color: #EDF3FC !important;
    box-shadow: 0 10px 26px rgba(3,10,20,.16) !important;
    animation: login-arrive .45s ease-out both;
}
.login-hero .title { color:#EDF3FC !important; font-size:clamp(2rem,4vw,3.2rem) !important; position:relative; z-index:2; }
.login-hero .sub { color:#B4C5D9 !important; position:relative; z-index:2; }
.login-kicker { display:inline-flex; align-items:center; gap:8px; color:#8BB8D9; font-size:11px; font-weight:800; letter-spacing:.14em; margin-bottom:9px; position:relative; z-index:2; }
.live-dot { width:8px; height:8px; background:#19B99A; border-radius:50%; box-shadow:0 0 0 4px rgba(25,185,154,.13); animation: dot-beat 1.8s ease-in-out infinite; }
.login-orbit { position:absolute; width:230px; height:150px; right:5%; top:7px; opacity:.42; pointer-events:none; }
.orbit-ring { position:absolute; border:1px solid rgba(120,166,207,.24); border-radius:50%; transform:rotate(-18deg); }
.ring-a { width:210px;height:76px;top:22px;left:5px; }
.ring-b { width:160px;height:115px;top:3px;left:30px;transform:rotate(38deg); }
.orbit-plane { position:absolute; left:98px;top:48px;font-size:34px;color:#8BC8E8;filter:none;animation: plane-float 6s ease-in-out infinite; }
.orbit-dot { position:absolute;width:7px;height:7px;background:#F5A623;border-radius:50%;box-shadow:0 0 0 5px rgba(245,166,35,.13); }
.dot-a { left:29px;top:56px;animation: dot-beat 2.2s infinite; }
.dot-b { right:12px;top:94px;background:#19B99A;animation: dot-beat 1.7s infinite .4s; }
.login-widgets { display:flex;justify-content:center;gap:10px;flex-wrap:wrap;margin-top:22px;position:relative;z-index:2; }
.login-widget { display:flex;align-items:center;gap:10px;min-width:190px;text-align:left;padding:10px 13px;background:rgba(255,255,255,.045);border:1px solid #304A65;border-radius:13px;backdrop-filter:none;box-shadow:none;animation: widget-up .45s ease-out both; }
.login-widget:nth-child(2) { animation-delay:.12s; }
.login-widget:nth-child(3) { animation-delay:.24s; }
.widget-icon { width:31px;height:31px;display:grid;place-items:center;border-radius:10px;background:#213D59;color:#A7D9F2;font-size:19px;font-weight:800; }
.login-widget b { display:block;font-size:12px;color:#E8F0FA;font-weight:800; }
.login-widget small { display:block;font-size:10px;color:#A8BCD2;margin-top:2px; }
.widget-pulse { width:8px;height:8px;margin-left:auto;background:#18B99A;border-radius:50%;box-shadow:0 0 0 4px rgba(24,185,154,.12);animation:dot-beat 1.8s infinite; }
.mini-bars { margin-left:auto;height:23px;display:flex;align-items:end;gap:3px; }
.mini-bars i { width:4px;border-radius:4px;background:#278DD0;animation:bar-bounce 1s ease-in-out infinite alternate; }
.mini-bars i:nth-child(1){height:8px}.mini-bars i:nth-child(2){height:16px;animation-delay:.2s}.mini-bars i:nth-child(3){height:12px;animation-delay:.35s}.mini-bars i:nth-child(4){height:22px;animation-delay:.1s}.mini-bars i:nth-child(5){height:10px;animation-delay:.4s}
.widget-check { margin-left:auto;display:grid;place-items:center;width:23px;height:23px;border-radius:50%;background:#D3F8EF;color:#078B76;font-weight:900; }
div[data-testid="stTabs"] { margin-top: 8px; }
div[data-testid="stTabs"] [role="tablist"] { background:#13263B !important;border:1px solid #2D4763 !important;border-radius:14px !important;padding:5px !important;gap:5px !important; }
div[data-testid="stTabs"] button[role="tab"] { border-radius:10px !important;color:#A8BCD2 !important;font-weight:750 !important;transition:color .15s ease, background-color .15s ease !important; }
div[data-testid="stTabs"] button[role="tab"][aria-selected="true"] { background:#243D58 !important;color:#F0F5FC !important;box-shadow:none !important; }
div[data-testid="stTabs"] button[role="tab"] p { color:inherit !important;font-weight:800 !important; }
div[data-testid="stTextInput"] { margin-bottom:12px; }
div[data-testid="stTextInput"] label, div[data-testid="stTextInput"] label p { color:#B8C9DD !important;font-size:13px !important;font-weight:800 !important; }
div[data-testid="stTextInput"] input {
    height:50px !important;box-sizing:border-box !important;
    background:#0F2033 !important;color:#EDF3FC !important;
    -webkit-text-fill-color:#EDF3FC !important;
    border:1.5px solid #304A65 !important;border-radius:12px !important;
    padding:0 15px !important;box-shadow:0 4px 14px rgba(0,0,0,.08) !important;
    caret-color:#8BC8E8 !important;
}
div[data-testid="stTextInput"] input::placeholder { color:#8197B0 !important;opacity:1 !important; }
div[data-testid="stTextInput"] input:focus { border-color:#65B9DE !important;box-shadow:0 0 0 2px rgba(101,185,222,.12) !important; }
div[data-testid="stTextInput"] [data-baseweb="input"] { background:#0F2033 !important;border-radius:12px !important; }
div[data-testid="stTextInput"] [data-baseweb="input"] > div { background:transparent !important; }
div[data-testid="stTextInput"] button { color:#B8C9DD !important; }
div[data-testid="stButton"] button[kind="primary"] { min-height:49px !important;border-radius:14px !important;font-weight:800 !important;letter-spacing:.01em; }
@media (prefers-reduced-motion: reduce) {
    .login-hero, .login-widget, .live-dot, .orbit-plane, .orbit-dot,
    .mini-bars i, .widget-pulse {
        animation: none !important;
    }
}


/* Unified live-mic surface */
.st-key-mic_card,
.st-key-mic_card [data-testid="stVerticalBlock"],
.st-key-mic_card [data-testid="stHorizontalBlock"],
.st-key-mic_card [data-testid="stElementContainer"],
.st-key-mic_card iframe,
.st-key-mic_card [data-testid="stCustomComponentV1"] {
    background: transparent !important;
    background-color: transparent !important;
    border: 0 !important;
    box-shadow: none !important;
}
.st-key-mic_card {
    background: linear-gradient(145deg, rgba(12,33,59,.98), rgba(7,23,43,.98)) !important;
    border: 1px solid #24486F !important;
    border-radius: 23px !important;
    padding: 16px 20px 14px !important;
    overflow: hidden !important;
}
.st-key-mic_card iframe { display:block !important; width:100% !important; }
.st-key-mic_card [data-testid="stCustomComponentV1"] > div {
    background: transparent !important;
}
.block-container { padding-top: .65rem !important; padding-bottom: 1rem !important; }
.hero { margin-bottom: 12px !important; }
.hero:not(.login-hero) { padding-top: 18px !important; padding-bottom: 18px !important; }
.strip { margin-bottom: 12px !important; }
.brief { padding: 19px 24px !important; margin-bottom: 12px !important; }
.st-key-mic_card { margin-bottom: 8px !important; }
.stTextArea textarea {
    min-height: 112px !important;
    height: 112px !important;
    resize: vertical !important;
    background: #071A31 !important;
    color: #EAF2FF !important;
    border: 1px solid #2B507A !important;
    border-radius: 14px !important;
    box-shadow: inset 0 1px 0 rgba(255,255,255,.03) !important;
    padding: 12px 14px !important;
}
div[data-testid="stTextArea"] { margin-bottom: 4px !important; }
div[data-testid="stTextArea"] label { margin-bottom: 3px !important; }

/* Final compact layout + transparent speech iframe fix */
.st-key-mic_card,
.st-key-mic_card > div,
.st-key-mic_card [data-testid="stVerticalBlock"],
.st-key-mic_card [data-testid="stElementContainer"],
.st-key-mic_card [data-testid="stCustomComponentV1"],
.st-key-mic_card [data-testid="stCustomComponentV1"] > div,
.st-key-mic_card iframe {
    background: transparent !important;
    background-color: transparent !important;
    background-image: none !important;
    box-shadow: none !important;
}
.st-key-mic_card {
    background: linear-gradient(145deg, #0C213B 0%, #07172B 100%) !important;
    border: 1px solid #24486F !important;
    border-radius: 20px !important;
    padding: 12px 16px 10px !important;
    margin-top: 0 !important;
    margin-bottom: 5px !important;
}
.st-key-mic_card iframe {
    display: block !important;
    height: 84px !important;
    min-height: 84px !important;
    border: 0 !important;
    outline: 0 !important;
}
.block-container { padding-top: .2rem !important; padding-bottom: .35rem !important; }
.hero:not(.login-hero) { min-height: 128px !important; padding: 13px 24px !important; margin-bottom: 9px !important; }
.hero:not(.login-hero) .title { font-size: 1.9rem !important; margin-bottom: 4px !important; }
.hero:not(.login-hero) .sub { font-size: .86rem !important; line-height: 1.4 !important; }
.strip { margin-bottom: 8px !important; }
.strip .cell { padding-top: 8px !important; padding-bottom: 8px !important; }
.strip .v { font-size: 1.45rem !important; }
.brief { padding: 16px 22px !important; margin-bottom: 9px !important; }
.brief .q-text, .q-text { font-size: 1.85rem !important; line-height: 1.35 !important; font-weight: 700 !important; }
.st-key-mic_card .mic-h { margin-bottom: 2px !important; font-size: 14px !important; }
.st-key-mic_card .mic-s { margin-bottom: 2px !important; font-size: 11px !important; }
div[data-testid="stTextArea"] { margin-top: 0 !important; margin-bottom: 2px !important; }
div[data-testid="stTextArea"] label { margin-bottom: 2px !important; }
.stTextArea textarea { height: 92px !important; min-height: 92px !important; padding: 10px 12px !important; }

@media (max-width: 800px) {
    .block-container { padding-left: 1rem !important; padding-right: 1rem !important; }
    .strip { grid-template-columns: repeat(2, 1fr); }
    .strip .cell:nth-child(2) { border-right: none; }
    .strip .cell:nth-child(-n+2) { border-bottom: 1px solid var(--line); }
    .report { grid-template-columns: 1fr; }
    .hero { padding: 26px 22px 30px 22px; }
    .hero .title { font-size: 2rem; }
    .q-text { font-size: 1.45rem !important; }
    .login-hero { padding:24px 16px !important; }
    .login-orbit { right:-65px;opacity:.35; }
    .login-widget { min-width:100%; }
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


    /* PilotPrep brand header */
    .pilotprep-topbar {
        display:flex; align-items:center; justify-content:space-between; gap:18px;
        padding: 5px 0 18px 0; margin-bottom: 10px;
        border-bottom: 1px solid rgba(111, 143, 179, .22);
    }
    .pilotprep-brand-group { display:flex; align-items:center; gap:22px; min-width:0; }
    .pilotprep-wordmark {
        display:flex; align-items:center; gap:10px; white-space:nowrap;
        color:#F3F7FC; font-family:'Barlow Semi Condensed',sans-serif;
        font-size:1.75rem; font-weight:700; letter-spacing:.15px;
    }
    .pilotprep-mark {
        width:39px; height:39px; border-radius:11px; display:flex;
        align-items:center; justify-content:center; flex-shrink:0;
        color:#F8C04B; background:#142943; border:1px solid #355170;
        font-size:1.45rem;
    }
    .pilotprep-wordmark .prep { color:#F8C04B; }
    .icao-logo {
        display:block; width:116px; height:42px; object-fit:contain;
        padding:4px 7px; border-radius:6px; background:#FFFFFF;
        border:1px solid rgba(255,255,255,.35);
    }
    .pilotprep-topbar .stButton button {
        min-height:38px !important; height:38px !important; padding: .35rem .9rem !important;
        background:#142943 !important; color:#EDF3FC !important;
        border:1px solid #355170 !important; border-radius:8px !important;
        font-size:.9rem !important; font-weight:600 !important;
    }
    .pilotprep-topbar .stButton button:hover {
        background:#1B3654 !important; border-color:#F8C04B !important; color:#FFFFFF !important;
    }
    @media (max-width: 650px) {
        .pilotprep-topbar { align-items:flex-start; flex-wrap:wrap; }
        .pilotprep-brand-group { gap:12px; }
        .pilotprep-wordmark { font-size:1.4rem; }
        .pilotprep-mark { width:34px; height:34px; }
        .icao-logo { width:90px; height:35px; }
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
    100: ("Excellent", "#2FBF8F", "Your answer fully matches the expected response. Keep up this level."),
    80:  ("Very Good", "#2FBF8F", "Your answer is largely sufficient. Add the missing concepts to reach 100."),
    60:  ("Moderate", "#F2A81D", "The core idea is there, but some important details are missing."),
    30:  ("Needs Work", "#D8483F", "Your answer is far from the correct one. Read the sample answer and try again."),
    0:   ("Inadequate", "#D8483F", "The targeted explanations were not found in your answer."),
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

# --- PILOTPREP BRAND HEADER AND LOGOUT ---
_ICAO_LOGO_DATA_URI = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAASIAAABkCAIAAACtqqokAABDKklEQVR42u1dZ2BTZdt+zsneSZMmXeneew9KoYBMAWWJIEtURERxoOLGhXsrS9kgiAyRPcvqonTvPdMmTdLsfcb340C/SgsCZfma61eapCdnPNdz7/uGcBwHTjjhxN0E7LwFTjjhpJkTTjhp5oQTTjhp5oQTTpo54YSTZk444YSTZk444aSZE0448e+hmc2Bakx2kxW5Jpx+pLgzZNlBudbS+47Fju7Ja0t/54Tv8weilx/+9M9KjclOfKQy2Ew2xPnUnbjHgP4VWSBZlYrfc9o61CYugzI21n1Ohh8JhgAAOA4+2VexO7ctMcBl43OpAAAUw9edrP/xaN37MyIjpPxunXXNyXp3PuPHhYkOFJv/U+74OI+5w/ycD96Jewnyg3+Kf13uWPJrwauTwt6cEl7QoF75R3ldp+GTWTEAAATDytq0Kx4Nf3lLUWmrJsZHoDLY/izo2PlSeqyvgPj3lCCR2YYAALQmR1Gz5sXxIc6n7oRTafwbVHrbe7vL35oS+fLDoT4i1vRU72/nJ3x3uLa8TQsAUBtslW06XzE7Usr781IHiuEao11jsvuK2b1HYNPJYh4dAFAj06EYnhoscj51J5w0+xualUYExZ4eFdD7zvBwMZtBPlrcCQA4XtrVpbW8tq2oS2M5cLmjW2dlUEk0MsnuQK85Dg5ASYtGyKb2fdOOYM4V4ISTZoAEQxiGU0jQ/6u5MIThOIbjOACf7Ktc9FDgsbdG5Hw8xteVlV2jdOPTg9w5i9Zf6v1+vdxQI9OjGC7rsTyc6Nn7/oGCjuS3js/89uI1v3i4SJZVoXCuDCf+Z2mG46BRYTxS1NmmMhHv+IvZYh79vd/LCA8hiuEnyroADqYkS5sUxjalaUqyF4dB4TGpE+I8N5xppJJJbzwSZrIiEz49u3J3+dwfc+b+mKPQWe0OtF5uGB/j3vtbpa3a9YuSq2V6i/3/RV+NTP/kmny10eZcGU78z7pANCb7ruyWWB/BhjONr00OZ9PJfBZ11ayYZ9ZdalOZ00JcW5XGYyVd3z2ZEOLB7VCbf1mckuDvAgCAIPBYmndqkBBAINSTt/3FIYVNPW0qU6SUF+Mr8JewVQZbZbuWw6D0/lZasGjb+eZHk73oFBLxjsWOvvlbSUqg8OF4TwCAweI4V939UJRb7xeccOL2cH8c+giK1cj0f12WAQiMi/WIkvIoZBgAINda152sf3FCyBcHqpZPDu81pVQG25d/VefXq3xErJcnhvZ6EW9JTnbrrQIWlUq+rgDfndP6ytaiqm8nUkjwqXL5G9tLajp1X82Jf2VSqHOhOPEvoxmG4x/tqThdLk8IcEExkF3TnRgg/PCxaAmfjmH4qXJ5Xr16VJQkPcT1Xp6VweKY+W12lA8vzJP312UZjuMWO2qyISffHUmnkFAMR1CcRnEmzTjxL1EaL1Yrz1QofliYGOMjwHC8VWWa80POvvz2xWOCYBgaE+M+po8Fdc+w7XxzVqWirksf62d6bkxQgIQ19pOsD2fG0CgkDMdXH6/LquzetzzDuWKc+He4QNadahgeIY71FUAQIMGQv5j9xiPhpyrkFvt9S4OyIdgvpxqTAlzWPJO855WhmRHi17eXREj501OlEABnKxVrT9Y/Py7IuVyc+NdIM6XeGuLB6fuOm4BusaHY/cv6opHhvFVjrA6Mx6TgODha3HmpQX1oRSaFBDfIjR/8UTF/uL8Hn7H/UntdlyHWVzAmxh1yrh0nHmSaPZrkdaios8dod7nq4ThX1R3nJ6BT76dDj0Yh0SgkAIDB6th6rvmDx6KiffhKvXXCqjMIBtafbvjuSK07n57oLwz34mEYTiRVOuHEg+ICqe3Ut6nMUd48MY8OQ5DFjo75+EyUN3/x6CASDGVVKDacaVy/ODkpQPgg3BEcx8vatIESjgPDnvulQKG1zkr3KWnVvjM1wl3AcK4YJx5Qmn17qObzA1VhXrzR0W4zh3gHSDhVHbpfTzfWdOpoZJKHC2P+cP/kQOGDdmty61TfHKr++emkAwUyGhmeN9yZ1+/EA0yz8jbtM+vyv5ob//7usuJmzdzhfm88Ei7m0h0oBgAgkyAK6UF0lKMY7kAxOoW05kS9K5c2PdW7j8QDuXXKbeebF48Oirn1IJ4TTtvszsNfwg525+bWqZ4eGfDD0bqWbtOEVVlPjwpcOi74Qb41JBgiwSQAAOERBQAYrUh9lyGnTnmgoEOpt7WpTJMSvZw0c+KBoBmLRp6WIn1+Q4GvK3vlY1GZ4eKiZg2D+q/JYMoIFestjl9PNx4ukhW3aEgQ9PW8uD8LOiQ8+shIyf09NwRBK+oaQvx9GHS6czX/t2iGA6A22NadaKCQoaXjgpk08vg4DxadkhEmHhvjDgBIuxNFXxiO4ziwOtBGubG+S6/Q2dRGKwCQC5vqxmMEurMDJRwalQRDAIagmznn630pQsqr7zK8vLXorUfDF2T6P7k6r01tPlvVfea9Ufc93dGBOM5k53uIXZ00+2/RDMfB6XL5u7+XBrlznxoZwKSRAQBUMvz13LhP9lV29lg8XBg3MIfqOvVlbdqxMR58FmXA7+jNjsoOXVWHrk1lUhlsZhsqYFE9BAwek9KmMqsN9glxHs3dxuw6pcZoZ9HJLiyqjysrwosX7sXjMgc+ptWBHi7sDPXkhHjyyAN56oPcOeoN04h8yJ+fSnp+Y8EjiV7+ErZzATlxf2jmQLHvj9S8MD5kWoqUdnWzv9yozoyQ7LvUrrPYPcDANDNYHZ/trzpR2rVqVgyXOcCJ2R3o1gstR4o6fcWs1CDhlGSpmEd3YVN7RQoMQ+1qc28NqNWBaox2hc5a32XYk9fW1G0aF+s+d5hff32VRia5cKhPrs4fGSl5c0oEbyA29uYcJwW6cOjk5ZPCAABmG1raqkFQPMaXz2VQnOvJiXtEM7XR1mNyZIZLejmmMdk/2Ve5/tnk9YtSyCToGvEFQxCG4xdrlPN+yunSWj98LPqhaPdrtDyDxXG6XL7yj4ph4a4/PJngJWTegOQqg+1IkWx8nKcrl+YuYLgLGLG+ghlp3u1q09cHa4a8c+L96ZGjotz6FsVAEBgeLp45xOfN30p2XGzZ8nxqZoQE4ADDcXI/L+i6kw0zUn2CPTh5dapF6y/JtRYYglg08vdPJoyP83CGrZ24FzRDUByG/mbooChusaM2B3YNxxwodrJUnhwo3H+pfeWe8s4ey0NRbvOH+/XlmAPBsioVe/Pb3fj0ncuGhHnxbvzrNTL9c78UtCpNUT4CVy6t70dSIeu7BQn1XfrtF1qOlnRNSfYaEelGuyqjYAian+l3vLTzZJn8iR9y3p4a+Via96VG9fjYa5kT6MYO9+K1q8xPrs6bn+k/J8OXRSOfKpcvWJ23YXHKI0lezlXlxF2nmYhDQzG8rEXjcTVnok1lMtvRa+wiHMc//7PKbEMMVuTVrUUGK0KjwJ/Pie2baeFAsc/+rGxQGFc8EuEvYd9MHUqQO+e50UF2BAty51znC9y3p0Y2dRs/21+VW6d6f0ZUr4NExKF9/2RC1KtH5Frr69uLySSoRqbPrlV+Oiu27xGeeSgQx8G8H3N8xayXHw4hhPb0VG8YhvZf6piU6HkzHhcn/lMgrVy58o45PwCAACDDMIbjb+4soZBIFAp8oVr55s6SBcP904JF0NX1Z0ewT/dXfvZn1dQU7y8OVHZqrCwa+au5ccmBIioZJsEQjgO51vLKliISDH8+J87ThXGNJCQOojbYZBpzebv2XKXydLn8RFlXs8KEYrjKYNOZHXYEQzCcOCChoOrMjka5Qa61hnvxxsa6Z1Uptp5tTgsWEQokguIohsf7uxwv7TLb0Ha1eVqK99s7Sw1Wx7AwSe8JEFfx/u7yR5O8hodLetVOVy59x8WWSQle99L9iCDI5bLK6LBgFtOZCPbfkGbbzjcHuXHSgkVzh/m5sKmHi2RHimUiDv21SeETEzz67vHZtcrVJ+p5TKrZhrSpzJ4ujFcnhsX5uWzManz9kXAAQFWH7su/qkdGSWam+fQXYhY7ery0K6dW6UAwJo3swqZKePQQD26nxnKqTM5jUsgkOKdWeaioM9yLK2BRU4NEOA4u1HTXyw359Wp/MfvEOyP4LOqHj0X/kdf21s6S5ZPCI6Q8AIEfjtSOjnZbNSvm8wPVtTK93uKgkODNWc0T4jyHh4t7TwCGoGhvfmmrpu9Z7bvUJmBRmTRnRwMn7ibNzlV2v7atODlQ+MnjMdNSvCcmeCIoTiZB1+zuOA4OFHQotNaMMHGTwjh3mN/7M6LKW7Uzvrn424tDyDBksCDPrMt/fmzw7AxfqJ/hd6Cg/a2dZWNj3BaODPB1ZTGoJCqZRFBYobN2aiyPp/uwaGQExXEAnh4Z0KW1bDnb/OvpBoP1Sj0bGYaI1nEUEjwr3ddiQx//7mL2x2O4DMq84X5jP8lavyi54LOxH++pyK9XBblxils0v55u7EszAMBnc2KT3jh28LJsUqInjoNjpZ0vby5a/XTSg5k45sT9xZ3MacRw/HJjz/dHakpatMmBwoUj/COkfAGb2pcq3TqrymCb9Pm5JoXxrSkRD0W7BbpxDhXKPtxTMTxcvOul9DaVaeHq/LQQUVmr5rXJYUNCXAkx6ECw0lbt+tMNJBh6bVLYgDGrDWca29XmlTOi+n/UIDeM/vhMS/eVhlkfzox+bXIYjUwqaFR/dbA6wc/laEnnlqVp3kLmU2vzDxR0vDc9akqyV169ymrH5v+cK2BRm39+xGRF+gb9/izo+GhPhSuPhiB4t946e6jPikcj7vHzs1ita7btnjNloljkchv/bnWgXZor4wd8XFm3YVU6EExlsKmNNqMFsSEYil3ZWHlMiohDc+HQ7pKdqjLYDBYHAIDLoAg5tLvxEyiGd+usaqPdYHHYEBTDcDIJZlBJXAbFlUvnsyg3f7vupDSDISg5ULht6ZDiFs2R4s6XtxSNinJ7f3okEaEGABityDeHaqanSpu7jRAEnsjw7dJanl6bf6ZcHiHlfTY7psdo/+JA1bOjA6elSktatO/sLF00OnByoqfNga05UV8t080e6psWJLqlyjQ7gsEQ8BaxxsV4rD1ZT7z58d4KGoUU7sn98Wjt53PiYnwEIR6cT/ZWfvZEzAczoiratK9sLTpQ0LHi0fDIED4AQGd2qPTWbw/Xrpod0xsfm5zoGSXlVcv0GI4HSDgRUt6/bpet7dQv+DmPeH3hw9Fs+i2sBwTFDhbKjpV0VXXoZD3mHqPdYkcdKEYlwWwGxZVLkwqZMT6C6anSpEDhHXcLvb69uLhZAwCI9uZvXJJ6Z+MoZhtyokx+uFBW26mX9VhURpvZhqAoTqWQOHSyiEvzEbES/F0eTfJKDBRC95hmV8gGQwn+LvF+Lq9ODFUbbAzq///ExRplbr3q4QQPHAdeQqbJhkz96oLe7OCzqB8/HuMrZm880+gpZE5P9YYgEO8n2PJ82hM/Zrvz6VvONZNg+PsFCb2M7YXNgebWq7Mq5JXtOqLpYkWbNtyLNzJSkhIkYlBJ9Z0GGhUOdOOMjXXfmd2iMzsI7q3aVxHrKzjyViaTSgYATE7yqusy7MlrW/RQ0MezYmd+ezGrUpFXrzr93igRh6Yy2Go7DW0qU1FTT2aEpHdbCXDjBLhx/r3KjMmKlLRcsTCxWylfv1ijnP9TbovK1P+/bAhmM9jUBluNTH+qTP7t4ZpJiZ7rFyW7cu9YOpjaYNt+rtmB4QAAhdbapjL5ie9YRs6lBvVTa/KqZPoBLs2B2hyoymCrkelPlHV9fqBqWor0m/nxni7Me02zXs8bk0buywoUw388WushYKAoDgDwF7OnfHlBb3YEuXM+nRU7McGzrE17qEj2w5OJvRsfBnBXLn3KVxcipbz9y4f1PZpKb8uuVebWqdrVZncBPcZHMCrSLatS0aWxzB7q26Y2Hy7u3HCm0dOF6SVkZlUq7A7MlUcbEuIq6zGXtWoJAeUuYDgQHFCvcObJEQFPr82L8xOOjnL7bdmQV7cUVcv04z7JGhkp+bOgw4Fhkd7817eX5H869r/ssJf1mH86VvfTsTrjVVuXy6T4ubIkPAabQSbDkA3BdCaHTGNu6TY5UAzF8D8vdRQ3aT56PHr2UN87InY2nGl0XOVAj8l2pLhzyZjgwctLhc767aGa74/UWq82h+cyKL5ilhufwaaTySTI5sC0JnunxtKqNNkRDMXx3blthU09Hz8ePTnRq78MuOs064/iZs2JMvlLE0IIEjYqDJ09lrRg0WdPxDIoJL3F8dKmwg9nRvfN8KCSYAzHX3445EKN8nSFfFKCFwQBHAdHSzq3nG2K83OZmiINcufwmVTiFtfLDTgAw8LFAIAnMnx1JnuD3HimUqE12acmS1efqH883Sc5UDjukyzi+L/ntMb7ubwyMZR49q5c2vvTo5ZtLjy0YniklL9pSdqrWwuza1UXapRXbzq5qLnnXKWiV6D911AvNyzbVHispJOw6LlMyrxhflOSpd4ipiuXzqKRSTBkRzCD1SHXWmo7DRuzGk+UdCEY3qoyLdtUWN9leG96VP/YzC3BYHGcq+ruI2Gw3FrVgkx/Fm1Qi1mutT75c+6ZSgXhHuMxKXOH+T2S6OUnZom4dBaNoBmqtyAKnaWqXbfhTOOpCgWG4Y0K41Nr81+dpH/jkfDrncO9o9k3h6oRFGPTyTAM4Tjo1FhifATbXkhbf7LhkSTp3ry2WF/B0FDXvg7J42VdYi79xfGhM9N9F63Nl4pYIe6crw/VHCrs2PFCeqD7jbQ1CAA+i5oY4JIY4DIr3WfBT7lGq2PNifq0YBGFBCMYhuMAx8Hr24sb5IY1zyQRxkO8v8v0VO8dF1omJXptONP4xysZYz/JqmjXEv5JEgyjGP7u72UXPhz9H+SY0Yq8sb2YGBICw1CghLPn1aFR3vxrvkajwDQKTcShRUr5jyZ5bTvfvGxzod7sIHLu2AzyqxPDBiPTytu0Rc09hKixI5jVgR4v7ZJrrQGDyORWG2wzv714vrqbkAGRUt6mJWlEQ+u/XxrJlUJy5dIipfwZad47Lra8uKlQa7Sbbehn+6vEXPrzYwcWqvfI+6zU246XdhGvOQwyGYamJEuPvJX556WOrMruEA9Ofr16+eSwvv9yoaZ79fH6Nx4Jp1FgqZD50ePRK3YUL99ajGH4hQ9H35hj10AqZB5cMXxBpr/B4nhnV+nPTyf27bV6skxe3qrt/XNKsldVh45JJdV16Tecabzw4egZaT4kGJIKWcQX2lXm3vGf/x2gGL5iR8mBAhkAgEqG5w3zy/tkTH+OXQMSDC3I9D/yZmacnwACAMPxn47W5dQqB6UWtWiUehvhghoRISG8jqfL5bd9QDuCfby3IrdOBQCgkOA5GX7H3x7Zn2P9zCJoTobf4RWZiQFCAIADxVbsKNmb3zaww+LePKRqmc7mwAAAFjvKoVPSQ12/mR+//1L7R3sr5g/3q2jXuQsY4j4piD0G++rjdb88m0w40CEAQty5GpO9oEkdIeVRyf/vacQBaFQYfjpWt3BN3neHa3672LJwdd6Px2ob5Ia+J8CgkeN8BQESdrPC5ClgTojzeDjeg/ioRWlctb+yN7DhIWByGZR6uWHhyIDPD1StPVH/3fz4IcEiNwGd6HHXY7RdqO7+r9Hsl1MNa0/WYzgOABgb4/7lnDjB36dY3QDpIa7fL0ggYjDtavPybcUIevthpG3nmlEMp5DgCfGeT2T4Em9+fbAaud0OhBdrlL+ebnSgGASBmek+3y1IuPneSqlBwl8WJ4s4NACAyYYs31ZcLdPdN5rVdeqJzh8ak53Poj43Juivgo7nN1zmMinjYt33X2pPCxb1zYU/VSGPlPJDPLjEnw4U++5I7eQE6c5l6TsutBS3aHAcOFCsvtOw5JdL837M1ZsdCzL95w7zGx/rsXCEv9GCLFyTt/iXgka5wY5gOA5Kmnu2nG8+8Mbwlx8O+fJg1cQEz1cmhu54cQiTRsZxsDe/fdv5litqNAmanOT1yb7KRH8XIZu64reSbeeb35se5cq50rzE4kDrugz/KY5pTPbfsluJXcbThbHr5XQR99ZCVRlh4sWjgwiF6lKD+nq7/j+iRWkqbNYAAJg00shIyePpPsSZ1HUZLjeob0+ULd1QYLQhhFvu3WmRLje9fRAyLcZHcOD1YUQORrvavONCS/+Wo/eIZl1aK/HbVgfKZ1Gbu03v/V4OQ9DEeE8IgoqbNdfUU5+rVExO/P9U98KmHqXeumxCcKAb5/0ZUe//XrbtfPO3h2o+/bNyfJzHyXdHvjU1YliYWMihCdjUoWHiN6dEHHtrxKQEj4/2Vnx9qHpndsvKP8rfnhrBoZM7tRYeg/rL6QYHiicHCj+dHePrynIXMPo2ror1FXRpLAwqaUK8JwSBT/ZVZtcqcYATezmO/+fmD2bXKoubewgl8IeFiUzq7Zj0S8cFR3tf6Zvyzq5SvdlxGwd587cSBMUAADPSvMU8OgmG5gy9ItBWn6i/jZa6x0q6qmV64vVLD4cGu99OeCY1WPR4ug8AAMPwk2Vypd56sy6QHqOdToGZtDvjI5mR6k2McfEUMGx2NDHAZesLaTAEIr35Z8rkqUHCvtVfle06B4qFe10RZQiKv/97+TvTIojvxPoK1j+bMuKDU5MSPL9dkMC7TkE0lUIKkHCkItaHeyrc+PTcj8a4CRhbzjW1q80UMrQnr/2dqZF2FFs6NnhqsvSlLYVVHbrwq1U2dApp0UOBv55ufGtKxIR4DxwHNApssqKz0n3i/VwgAHrF7B2xeXRmxy3toPceTQoj4b5PDBCmBN5mgwk6lbR1aVr8G0dRDJdrrWer/raT3gxUBtuR4k7i9SsTQwlfw+IxQetPN5ptSEGjuqPH7CNi3dIxew8o4tKeGhlwe5cGQ9CjSV778tv1FkdZq1autbrxGTdFsyHvnCDBEPvuVwTb7CgMQ2ffPgH6OBlHRbn1lqz9dbnDlUvLCBP3sm5XdkuQG6debqiR6ZIChRCAurQWhdZSI9OrDLa8OhWJBPuImEt+LciqVMAQpDHa15ysn5Tgeay48/3pUXWdhpIW7QsbL0dK+e9Mi3QXMOL9XJ5em9/XXsAwzI5gp+7+2E6LDZH1mNUbpz/INNuX3068iPHhi3m3n9kU5sUNcufUyPRGK3K2svvheM9bcjn+ntNmsiIAgJRAYZjnlT3RlUuP8xVk1yrbVOYL1UrvDNbNH9FgcdRcNaWmp0gH0wYqzJPr4cLQyxxWB5pXr75mNth1afb0yICsSgXtfrSU8XVloShe2aGN8RGYbeiGM43fzI/v/TSrUvHR3soXxgXTqfAn+ypnpHnrzI7Cpp6zlQocAKXO+kdum5hHTw8R5TeoAAAwDGhk+KO9lT8fr//8idhYX0G0N9/HlTXxs7MjIiUAAuWtWoXWOj7Wo7hFc+8v1uZAZw/1ecCVxsp2HeHpFrKpZPj2DQ0SDD2a5PWZrAoA0KmxWOzozad3mWxIbq2SUAtnpv//HeMxKWNi3PLqVWYbcrG6e+YQ75vP3u7SWlX6K5NZU4IG1QbKS8h05dJqZAAAUNLcc7NK45Jxwe095p+P1d37ERIwDL0xOfy3i60xPoJGhYHPovYqaR1q88rdZRqT7ZP9FSQYDnRjv7G9JDnQRaGztapMEIAI86m526g12c02lJB+3XobAEBtsL35WymdQmqQG5ZPDpuc6OknZkMA/HW5w9eV9dr24nt/pRAEXhwf8srEsAecZmY7AgCgkuFwKW8wyRYwBL0+OXz2UF8AAItOvqXc1OZuIxHXkvDoKX16VJNgKClAyKGTtWbH/oKOT5+IFbBuVgPvMdp0lismYpD7oJLmmDSyVMgCQAkAqJMbbpZmTCrpw8eiegy2nVddTPcMGIbnN6iC3DgHL8t0ZntvBUphU8/Heyty6lQEeRAUJXbZA5dlEAR8XVkjIiQcBuVkmbxGph8wtKXUW9/fXZbg77LuRP256m5PFyYMoC6N5Wxn933h2GNDfD6cGX2DAaIPCBwIDgCgkOBg98EapQI2VXBbhmh5q65TYwEARHrzw//eq2JYuNhXzC5p0XTrrMeKO2dddYr8s8ZuR4m8Kj6TMviOSV5XMxu7eiw3SzMAAI9J/empJDadsv50A3YPV6GnC3NaipTHpL646fKjyV4zh/gQavTi9ZcuN/UM+C9BbtytS9Ni/QRkGKrr0n9/pHbdyYYBvynrsSCo+nx196QET5MNeXZ9/rvTIxP9XdpVpgaF8V5ybOGIgK/nxf0r+mEhV9qwwx73b1jHmhNXFKuMUNdr/F4sGnlSgieRA71qf+X0tJvVG+0I5kAwAACHSRn8Ztcb5FAZbLdAM0Lx/XR2TKgXt11lxnCA4fjdzpoVsqkvjA95eUthu8r8xytDj5V20SkkmwP7aG+F2mh7amTAhjON/f/r63lxEVIu0T8n1IPbW1fWH1YH6sKhnnxn5OXGnrx61cE3M5dvLRJxaJc+Hbf2ZH233nYPCAZDkKcL48lMfx6T+uBzrFNjwa+e+f2qDe/SWggtBgAwe6gv1E9zfW1y2OcHquwIVtGuK2vV/mMOx1UpjRGBchaNTBk0zXp3TIPVcWs0AwDwWdRl40MI1+fGrMYYn7vYMj7Qjc1nUh//7qIDwWN8+fsvdWTXKTvUFiaNdKy4MyNUXN6mHfAfF68vWDo+eN4wPw8XhtmG3iAZigRDHgLmd0dqFTprbafegeKR3vzSFs3sH7KXjgvWmR2Nd1Om1XfqF44KzPx7IfYDjt4AFwTA/eom9N6uMkKUpQQKB6zo5TAoD0W5Ed75zWebYn0FN+PDRLErsVDa1YYxgzPPSFfdWtgt06wXrlyaQmstcKjv0q1MDhS6culLN1z+/eWhRBwJQTEHio2N9aCRYZXe+s60yC/+qro0ULB/fJx7jUz3/IaC/a8Nw3B8/bMpQ9890Vup0RdUMjwm2m1KirSqQ3espPOZUQEwDBHK5OPfXdy6NM1oQQ4Vye7SNRosCJ/5L+uaqjXb+4riew+l3nb6amTl/RlR1+PDs6ODTpTJERTLr1crtNYbNLf+fy8AjhPGEAxBMBjstd2g1dIt0CwpQPja5PDZ32ebbHd+SDSfSf1ybtw7O0ttDjRAwmLTr7Sa4jIodArMopET/IV8FqW6Qy/i0Ew2xGJH+1rV/hL2p/srqWRY1mNh0Uh5dUoJj260Gge8szgAHAaZRobFXLq3iHVl6eBAxKGt/KP8hwUJK34ruRvJwSwqafPStNh/8wQZ6H7w7EiRTK61AAA8BIzeVmL9EebJ9RExGxXGapmusKnHw8Xz5g6PAwDoVBKJBA365lz3o1vTRycnem5dmnaDpr+3jUkJnjl1SjGfPjVFWtF2JWLoQLGcOtVTa/K+/KvaS8iU9VhkGvOKKREbnkudEOdBKNN8JuWlCSFnq7oxHLz+SDgAeEFjj0Jva1YObJ7ZHNgHe8onfXbuYo1SyKH13hqD1TEq0i3eV3CqXD49VXrHL9CNT9+wJLXvkLR/C/qqQPeeZjYHdqmxh/AHTkuV3qBXp5eQmREmhgAwWpFz1TeVV0C0DCQYclcv7JbNvkeTvVbNiuGz7qTtTqPAaSGin47WvTwhNFLKP1N55R7VdepPlnXVdhp2ZrdsOdtULdM/muTVpDBMS5H+8mzKrCE+AAAXDu1oSReFBC+fHJYZIXHl0nfntK7cXX4916iYR39qRMB706OkQmbfAEunxsJnUV6eGLYruzXaR3BnnexcJuXT2bGPDfEB/0L0GG338de79dYTpV04DphUUmqQ6AYWFINKSr2agL4ru5XI8745YXZncGeUxiu8hKA5GX4ak313bhsAQGd2UEiDNYw5dLKARWXTKYHuHL3VsX1b81tTIgAA3x2pJRxBOA7yG9QfzYyW9ZgbugxNCmOoJ/eTWTF2FCtv1c7J8J05xKdBbiDB4HCR7FCRbMB2XXQK6bsnE6Yle4m4dBwHSzcUzBvu3/vp7zmtU5Olni4MFw41zIubHuqqu63c1r7Pz+pAiRjRI4leCzL9/6WK4r2PKPZFTYe+udsIAPCTsPtWCQ6IiQmeb+8sVRtssh7L8ZKuiQme9/JUydffAm4nM5jIXXhxfIjaYHtla5G/mA0PzkvDopFFXJqvKwsAIBWyKtt1OrODQSUZLP+/0FV6a7PStHxS2JkKxTPr8ve+mlHc0qO3OH56KrG52/T9kRoOndKoMG7KanRcp5aJy6RkhotFXDoAoF1tblebY3z5xEcmG3K6XPH1vHgAwLAwCRmGJyd69f312wCG43Wd+u+fTBTdnfZm/9v2WC8+O1BJ8Dzam/+PnW08BYwRkZI9uW0AgJV/lI+Ncafcw9C//fpFdINKwKdRSDWdelcO3ZU3qJVEJcM4hpvtyNHizpNlcqXBtmzz5dIWbc3VCgUAAIaDAwXtjyZ5ZYaLp6d5T/rinBuPvm1pmgubNiwcN1iQ5m7D5weqeznGppOXTw47WdqVXXsl3tIr4nAAVuwonpIs7ZXypS0aPwmbiHsIWBQExSgkeJB6o9Zkr+rQM6n/+ibE7vz7NqCwQ22+UK3sdSTeTBOR96dH7s1rw3FQ2qqpkunuavzpWpoh6F2hGZtOPvDa8Clfnr/UoMYG0VbVhU37bHbsuSrlnrwrmeBbzjb3/5q/mAMAABBI9Hf58UjtuBh3Qv2GIYjHpERI+ZFSHgAAAgAH4KFot3hfwcd7K3r/3ZVLQzG8pEVjdaBKvW1Bpl+vo2XtyYYvn4gl/tSY7D1G+wd/lCkHEaqGAIj2ERxaMfxOVRLdR/RVVe5g89ybwZcHqwkTy13wtzzGGyBSyo/25pe2alEM/z2nLUrKv4GqRSZBJBKMYCiGgbt6YYMVqW58+sYlKamDG3JrdSAYjlP+aa/ad6n9aEnnoULZZ/srNy5JdWHTnl2f/9flDpsDBQC0qcw7LrSkBouWTw4LcGMzqeTPD1SjKJ4ZLnlmVMCwcLELm7b/UjsMQRtON340M7pXF6ru0JNgKN7fhRB0uXUqndkxYMzt5pEcJNrx4pC74ZK9v7iXNFMZbBevirJXJ4XffJ7x7KG+RAe0/HqV+ub8N3YEu6sm6B3Ya8M8eZuWpKa8ebxvHPOWYLGjKoM1LVh0tkoBAKQ2DHxrSlo0r28r9haxdr2UzmFQMkLFjw/xWbQ+f+Uf5U9m+sf6ChwoHurOTQkSHSmUVbTryts0OADnq7sv1naLOHSFzlLepuUyKX4SdlKfrfFclaLXz95jsBksSIPc0Dcud6sQcqjrn03+NzYhHtim7ZN1eS+F2fmqbqKhC40MT7oVZ0Z6iKsLm6Y22Aoa1XVdhhu0YYWu7rUYjg9+B7nB1nxnVJpgd875Dx9atrnQdFtCAMPwwibNvOF+kd68Nx6JOFTY8cVf1ZcbB8gS7jHa1zyTTJRRQxCQ8On7lw+raNd9dbDqxU2FAIAGuWHzuaZrXBEYCoj4ps7s2Hi68fg7I3v9wg1dhpw6FeFqxwH4I69tdobvheruBH+X28u+oZDgr+fFRf9Ty6d/EXqnMeIAoPeKZyiGFzX3GK0OAMC4WI9bSlkOcudEe/OzKhUGC3KqTH4D/ySFBJFJEHAAix0dTBegXpHY62u4KzQDAER5839/Kd3qwK7ndgM4+HhvRZvaDAGQFCisaNNSSPDX8+MBAAiCfXmwWipkHC22ak32GWk+EAQ9szZf28+lbrQiR4s7U4NEvdYwDEPRPvybaYUJQWBBpr/e4jhS1Jlbr1o1K4ZMgub/nLtqdqyERwcAaI32k2Xyt6dG1Mr0H7waTYIhBMVe2lyIYviICMmJMjkAwJVDXTU7FsUGGJZ75YbCkLvgf2rUmJBNI3QwHAcWGwruyVx7sw3Zf6kDwwEJhpIChbeUsuzKpacGi7IqFQCAzWeb3pwS3rcV2t8f1pVURrMdudk42w2dXsSL/o0zyHd027uudC5u1tR06qelSuf+mKsy2GAIalEajVbU04VR32UI9uBOTPD87nDt+FiPrErF7KG+jyZLmTTybxdafs9t7bvN2BzobxdbzlV1b1ma5uvK6hU4PNY/Jwpy6JQXxoWIebQZ31zMq1MNCxdfalBNS/Em6tlwAA5c7nhiqO+evLZYX4GPK6vHYOMw6VkVCiGH1q42l7VqeUzKvuUZjXKjHcXGxriD/wZgGCLDkAPFERST9ZjvjcHZIDcS7QOYNLLNge7Kbr1FG/LKixal6Wxl95jrPCwqBSZKZvRmh80xWJqpDfbejeku0uwG8HRhzPj24s9PJX45J+7lLYV1XXoEw90FdKsDXbgmb+Vj0cPDxT8fq7OjWGFTz8hIiRufMSHO46EoN1cubc3Jei6DqrfYbQ4MgiAOg0IhQ6v2Vfi4sjLDJTG+Ah6T8vgQ328O1t54Q9JbHM+sy393WuTEBM9LDerfLrZESfkvTQy5co/0tsp2XVKgMKdW9e7UqIvVyq8OVv352nABm8phUBAUZ9HIX8+LJ8Hws+svnVv5EPgvgUomOVDEgWK1XYZBFvN3qM2FTT0YDiQ8emKAy/WiJm/sKCZcEgaL46M+7uLbwBcHqkZESAYMoDGpJMKzYrA4dObBZrG2q6/k93n224nuUfDOlUufmuz17q7S5CDh3lczHCjWpbG4cmkoBrQmx6tbiuQayzfz43fntCX6uzy9Nt9xdcxfSpDQlUtPCRJ+Ojt2TIz7jwsT9r+WsXNZ+pdz41ODRXvy26d9feHlLUUFDWpf8ZWWRrTruywLm3rURtsTGb5eQmZxsybUk0sksCAo9uKmyzG+/I1nGn9cmKiz2F/YWKAy2CAIRHrza2R6pd66/7Vhw8LEb/5WEuXNk9y/UNJ9AZFJaEewqnbtIC2Yo8Wd83/OXfBz7qazjdczh9pUpvNVd6zhbHGLprZLP+BHAjaVx6AAADAcNA2uAMpsQzp6zMTrwH6lOndemuEA2BzoNWsdgsDyyWFrT9R/8Ef5ukXJW54f8uz6fB6TgqIYhuO1HfpdOa0rHo2YmiKVa60ZYeLPDlS9Njmsql23O7ft9Hujvvqrqltn3fHikL4ZFWOi3cdEu6sNtqxKRW6tKsSdg+O43YFF+wgC3dnbzjWrjQPsTzYHtvFM49BQ8fvTI17aXBTqwY31FXx/tNZbxOpQWybEuYd78Vb+UVbepksJEuI48BaxvITMzUtSo30FL28uLG7WHFqRCf5jiPLmn6vqxnHQY3QgCHbbqRUIhu/KadWZHRAEeAzK9fKA151ssCEYQe/5w/1Jt5WGguH47rw2jdFOWOMRXvz+h3HjM1x5dNChAwDkN6jnDyIhrl1tVuqueMjj/AR3l2atStNflzuUBttLE0Kv6T0o5tIXjgz44WitweJ4b0bUxudSe2c3oxi+/ULLc2OCpqZI39tdmugv7Ogxf7SnoqJd+/6MqGB3zrcLEn493fjqlqLZGb4jIiR9NQ0hhzY91ZvwyPed1ukhYLz5W2n/YMiu7NYpyV6/Lo6gU0irZse8sb0kxIMr5NASA1xOlys+mRXdrbceLurEcBzFcDuCDgsTzxriw6SRFvyc+1dBx4JM/we8p+LdwOREr/PV3TgOipp7FDrrbZtnbUpTXr0aAMCikUdEug3oy9WY7Hn1Vwul033XLUq+vd/CcBxB8Q1ZjQiK59Sp9BZHf88El0EJ9eSerVQAAPblt386O5Z3u9WAVR06mcZCXBrRVf+uKI0Iin3+Z+XMby+qDHaF1kpMUbkG01O9XTn0oyVdj31zsUlhfGpkAJ1KInyGdZ2GSw09Lmzq21MiVx+vb5Ibt19oSQoQxvu5EKe+ZGzQikfDfznVsOTXgusF1vrCT8zun5gSIeWtfjppydhgIs0qxkcwPs5j+4Vmndn+6f7K96ZHurBpjXJjaYsWAECnwFQyaVqKVK61zPjm4oGCDiad/OQIf/DfQ4CETdyxkhbN9QrYbwYL1+SZbQgAgM+iDrtOCXlxs4YYQEd0tL99zw0EjYl1J1yU56u6ZVc1umswLvbKKAWFzrrjQvNtanA4/tflDiIJNnKg3Ms7QLMOtXndqYbY1482K00fzozu1llQDN+U1dh/lUf78Imb2642L1idt2xzUY/RPivdl9h7dma3FDb1lLRojryV2aI0vTc9sqnbuPr4lXF1FBIc5sXb9sKQtGDRxM/PvbOr9GKNskNtvl4cOcKL17f/ka+Y9dkTsdkfjYmQ8ghhaLQiq0/UX6xRfjo7NrdOdejNzGqZvkVpKmpSEy1PkoNECp31tW3Fj3+f3aI0AQDGRLtF/Q8FxG4eQ0NdkwJcCL3juV8K5DrrbciWndmtxFwyCAKfPxHLuU6HxtIWTY/RDgCI83W5poPVreu6PG8hi5CQx0u6BvzOxHiP3kSCLw5U1XXeznSEizXKXTltAAASDD0UJek/YOAO0Oxoceea43V+YvaTIwI2ZjXaEay526jQWc+UK/rL6FcmhhIDuTEc/+V0w6J1+ZMTvQiXerfOpjc7Xt1aVNqi+XFh4sUaZbyfiwPF399d1nK1RpNBJT01MuDQG8OTAoSnyuWf/lm1bFPhyj/KN2Y1/nVZVt2ha1IY/ros25TVtDO7lUYmJQUIR0ZK5g/327Us/Y1HwntVgg61+YM95Q4EmxDvkVunWv9sckOX4dWtRWqDjehvFecnmJPht+TXSz8dqyO2Cx6D8tLDodcU2plsyMasxv95mgk5tMWjg4g+qK0q0wsbCrr1t8a0khZNb37puFiPaSnXLW/der6Z2KATA1yIeOZtI8id29t7Z82J+t4ZnH1BgqHvFyQQmS4dPZb3d5fdqssxu0b5xA85VjtKeNTnDvPrXxFzB2yz2UN9s2uVQe7cZ9bmd2ksfBZ1VJQkUsp7e1fpiEjJNfp3apDo/AcPjfzgtEJnxTD8SHGnQmf9fkHCI1+cN1gcPBZFY3JM+vzcmmeSvpkXv3B1XrAHd1KC58xvL747LXJCvAfhGBRyaI8keT2c4Gl3YDqLvaRZU9muK27WlLRoTFaEz+zyFjHTQ12XjA3iMqkwBEgQ1Gu1Yzh+uKhzxfaS759MOF/T/ddl2Z5Xh54o7XpydR6FBJNgqLPHyqaTNz6X+tKmwvPV3cQj5zEo5z8aHSW9VpTtvNi6bPPlLo317akR/9tMm5nuc7aqe/2pBgDA3vx2GoW0blHyTQ7IVOqt07++QLQbc+PT35sWeT3nR6PCSCildCppXKzHIIskyDD0aLJ0x8UWAEC93JBdqxoVOUCPg+Hh4kWjA785WINi+O68NosD3bks/SYbfZe2ap5Zl9+uNhNq6vpFycEDzVcgrVy5cpAPgEqGOQzKT8frAt3YbnyGG58+JFiUV6822ZDUYNE1MWsIAq5cenKQ0GhF1Aab0Yp0aiw1Mn1SoLCwqWfZhJCcWmV9l+FcdbdUyPzw8eiCBnV+g3rRQ4GnyuQ5tUoKicRnUQk7AYYgChnm0ClB7pwhIa4T4jxwHLgLGJ/PiRsS4hroxmHTKRQSTCZdifRrTfZLjer1pxob5IYXJ4QcLJQxqeQNz6XszWtftqlQb3EkBgifyPB5e1fpw3Gef+S2na3qxgEQc+njYt2/nBuXFizq76pSG+1xfi7rTzWQSXBSgPDer34EQS6XVUaHBbOYt5N60q42b8y6kpv25qMRN+jlDkHQqEhJeZu2UWHEcFDeps2vV/mJOSIu7QZkUBtse/PbJ312nuhkSiXDH86MfjRZer1C4Cd+yK7vMgAAhGzal3NjGdTBioEgd87GrCbCatKbHdNTpf0T9mEYivDi18kNdZ16HAe1nfpzVd0+IpanC+N6uT44Drr11j8LOp5Zm0+0QuMyKB89Hj1vuP+AF3YHaAYA8BQyDxbKXLl0MZdmdaBNCuO4WI9lE0J9XFn9TxQHoLi5Z2io+LEhPlIRs8dgL23VmOxol9aaFuTKppPPViksdjSnTpUZLpme6s1jUffmtZFIcFqwqLJD93t2q6zH4i6g928kWtys0Vsc/QdDd6jNv11s2XahxeZAo735LUpjWat2eqr3rKE+bUrTEz/kKHRWGILmDfPzEbPWnmgw29HSVk2IB++5MUFvPBqeGiTSmOxhA9kJARJ2UoBQwKJ+dbAaw/FBhm4fZJoBAChkOD3UtaHLUNtlAAA0d5sOF8kq2nUoDkRcWt9u+BiO13cZtl9o+Xhfxa+nG4mcchad/P2ChKdGBV6vV2mbyvz69mKiYnDx6MDJidLBF5SSYEhrthNROIsDnRjvJRyoypbLoGSEucq1lqp2PQ5Am8p8skxe2NyDYLiER2f1uTQUwxu6DNsvNK/aV/nz8TrCjIRh6N3pkc+PDb7ejnNnHPo0MvzFnNgh75wUc2nvTY98IsMPgsDakw27slt3vzzU7e/BXAiAxADh9K8vpAQKX5kU9v70qMKmnh+O1naozYeKZF/Ni/v6UI3WZFfpbU+vyy//akJmuHhoqOsfua1LN1x+elTAiikRR4o7H/nivBuf/liaz6goiYTHIJ4HhuOEI5543aWxnCqX/5HbptBan34o4M0p4TvOtyzbfHnVrNiZQ3xIMIRi+KQvzhEbrZhLf3FC8AsbC2EYivMVbF2aluDvIuuxfHu4OrtG+fvLQ6+/zYM5Gb7dOuvLm4sgAC0dH3w/i43vMrxFrANvDH9x4+U1J+oRDO/W23Zmt+7MbiXBkL+EHeLOgWFIb0GqO/QK3d8aXLvzGRufSxkX53GDg2+/0EyMPYAAeGF8yJ0q2l48OujbQzVGK9KlsWRVKoI9Bu6V7+XC3LA4VcylrzlRb0ewLq3lj9y2P3LbIAgKlLD9JWwaBTZYkMp2nVJv7evc47Oo219Iezj+RjUE0J2qIMqpVRY0qudk+Ak5tBal6ZtDNTK1CYYhNz7j+wUJ/SV1Tq1y1vc53TprqBc32psf5c1349NhCJqSLK2W6WZ9l13XZaBTSNtfHDIt5UqfKa3JviuntbCpx5VL9xezIAjq1lnVBhuC4UwamUaGS1s1OpNjWLjY6kBNNoQCwyIuTcyjQwA0dxvlWmucn2DmEJ/e/exUmXz8qiwEw/0krPWLUjLCxLtzWgEAKr2trE1b3qat6tBxGJTfXhwyKsrtHzxpGP7Zn5Wbspq2LE0b8k8tK+4gLFbrmm2750yZKBa53N5TS3/3JPFat3kG9+aiRnYEO1Qk23CmMbdWdeNOezAE+bgyR0S4vfRwSKQ3/wbEMVqReT/l7r/UDgAYESE5/d6oO0UzgxWZ8fUFYvT5nAzfXxan3KA3jgPFDl6WbTjTmFev6jHe6NIgCHiLWGOi3V4YH/KP/uc7Fp5ODRYRy6tRYVi+tVgqZGpNjomJngaLY+v55v4NZ4aEuG5+PnXODzklzZqSZg2RFuAtYuXXq5dNCN7wXOqLmy6XNGu2nWvOjBATuZh8FvXZ0UE6k71FaaqR6UtaNPVyg92BegqZbDqZSoGpZJhMhuhUEoJhDgRrUhtblKRgD06UN396qrePK4vHovY+O63JvuZkPYLhMT787xYkBLhxVmwvPlOpaFeZtWY7sfkI2NTdL6ffoDcgAOBCTXdygJBGIa2YEiFg08gk+F8knehUUoAb+yolbsEan5oszQyXVLRrT5bKj5V2lrVqr5lg6sKmpgSJJsZ7ZISJQz25/9jUvl1lUuqtxMk8NTLgDvYfYdFIU1OkzUoTimGNCqPRityAZhQSPDVFmhkhqezQHS/pOlHWVd6qvcZFKWBR04JFExM800Ncg9w5N+Msge5gPSyG42cruxf8nPvSwyFKg41GItkQdOGIgCd+yPlyTtywCDHUL6i3M7t12abCa1r7k2Do9clhc4f5bT3fvP18y8wh3u8/FsWhU67nxSpr0zXKDUq9TWOyQwDwWVQxj+YnZkf78MXXKRowWpEP95RvOds0d7j/UyP9f7vYumpfxTUZI3wW9aeFiUQp7vVQ26kf+cHp0THu6xcl35fBLoOUZncKVjtaLzd0aawYjjNpJKmI5S1kDr5d9oMAix1tVBjkWiuC4gwq7OPK9hYyb7XH1J2kmdGKrDlRnxwoXH+qHsXwucP9D1xq9xIyhwSLNp1tWr8ohdUvIolg+F8F7WtONOTVq64pPvV0YSYGuNDIcKPc+HCC57IJIS5sKqE0q/Q2IirNopMlPLqER+//RBEM79Zau/VW4rAMKknIoXkIGFQybLQ6vjlUc6CgI8idY3Ngl5t6OtTmv+9/5ORA4eIxQVNTpDfoCobjYE9eG40M77jYMirKbdFDgf9Zmjlxj5RGAACbTl42IcRqRx0oHurBPVepqGjX5dWr6RTSRzNjBuzlQIahqSnew8Mlzd2mSw2qqg59vdzQoTaTYSjEkzshziMpQMhhkJV6+7789tx6VVFjj97qsNpRBCMmbkEMKlnCo6eHisbHegwJccVwPL9efby060J1t1xrsdgxB4pBAJBgiEYhcZmUeD/B0FDXCfGeCzL9jVakqElDp5AqO3Qohnu6MALdOOFevORAob+Y3T+W3187n5LsRSLBHCbluV8KpqVK+xcaOeEEuOOpw1QyTIKhGWneObUqokpy4Qj/N3eUzkr3IcGQymATsKj9JY+QQ+MxqcdKOhP8BU+O8GfRyBiOa032apn++yO1F6q7azr11yM2BCCl3rr9fMt3h2t9XVkwDDUpjEIOjUMnWx2Yzmy/RkiWtmg2ZTUBAILdOcPCJSlBwqXjgvlsKgmCzDakol2nMliTB2qihOF4eauut7UjjuMQBJFJMIbjJ0q67AjGY1C69VYhm/a/oSw58eDSjNjjzTYExbCfFyYeKOgQsmm/LE6mU0nHSjq/PlizeExQr+fwb+dBguYM81u+tWjpxssUEuxAMIvjRo0nwjy5o6Pd04JFfmJWUbPmaHFnmBfv4TgPAIEjRZ2lrZqH4z0SA4RtKlNOrepUmbyyQ3fNEeq6DHVdhl9PN0AA0KgkKgm2I9joGLcv58QNbH44sIOFHQTNHCi29mR9gIQzPtbjcFHnL2cav1+QkFen/mBP+Q9PJoR58ZwLy4m7SzMYgp7I8JuV7nuwUOYvYXMYFAgCWZWKeT/lPpLktfNiiwPBHh8o89rXlbX5+bTzVd1rT9afKlcMyDEahfRQlNvzY4NSgkQcBhnDwHO/XDpS0rllSVpmhIRI4UkJEhU0qB7/LmdUlGTzktQpyVKDBSloVK8+Xne8tKt/LToOAIbh6RGuS8YEDQ8Xc64zPtNiR4nscgzHN2U1vrmjlEaBXxwfsu5kQ0ao6/g4dweKpwaLRFy6c1U5cRddIP09BBiOk2CosKnnmbX5aSGiVqXpuTFBq0/UT070mj/c7wZ+Vb3FUdTUU9qqbVQYu3UWCIK8RawEf8HwcLGExyA8HEVNPc+uz3cg+Ppnk/uHqvLrVc+uL7DYkc3PpyYFXGnR062znq/uvtzY0642OxBMwqcHSDjRPvzEAJd/HE4r6zF/9mfVdwsSDhR0vLe77MeFiRequr8+VCPi0A68PuylzYVeIubmJWlOF4gT95RmBCratc/9UsChUwRsqtmGyHXWd6ZGfPlX9dfz4m9ycumA2H+pffm2YgaVtHlJaoK/S/8+70QN4rPrL2mM9k9nxz42ZLATjxrkhoVr8sfGuG862/j1vPiH4zy/Pli9+kTdtqVDkoOE+y91iHm0UZFuTpo5MYCKd1ePnl+vGvNxFgRB215Ii/Lm13UZ3pka8dTafD6LGiC5/UZkh4s6Z353kc+kXP5sXGKAcMBZChAEEvxdLnzwkKcLY+5POXvz2wd5LWY7erG6+8M95ZuXpE1O9Pojt/W93WXLJ4VlhIvpFNKsdJ97zzEn/i24M6nD1yUxDEmFTBzHSTD056WOADdOu8q08rHoWek+Ej6jqLmntlMv5NJo5FvowqfU2z7aWxHuxVv7TLL4n+qRKGQ4I0ws67HUdOjTgl3/UTO84e9aK9p1X8yJHR3tfqiwc8mvBbPSfd+cEnFfotK9GGTqsBP/I0oj4WMAOB7+yuE1TydpTHYmjTw2xl2lt2WuPMVnUb+ZH58ceGslJCYbYnNgN9+TQ22w0SkkFn1Q/h4Mx7t1Nhc2Nb9eNfen3IxQ1x8WJgpY97kvCIqiDS3tPl4edBrVuZr/0zQjMOXL8+FevMVjgqRCZlFzz5cHqltVJjqFJORQl08Kq5Lpn3zgB+1hOH6pXj30vRNjYty3vzDExRmMduJBsM364vVHwmU9ZqIBck6tqqRVEyBhS3h0MY/+zq7SGpnePIjpEPcAOA7+LOiY/s2FzAjJN/MSnBxz4kGUZoSyx6SSS1o1r2wpYlBINZ26ucP8jhR3xvoK6BSSt4j52uTwB5Vj+OZzzSt2lKQECtctSv4f65LvxP+ONAMAsGjkLo152lfnnxsdiOL4nAy/ui7Dgkz/shbtJ7NiXp0YhgNgsiI/Ha09XS4ffE/zOwWDBflwb8XTa/LTQ0S/LE5xcsyJB1qaEapXU7chr0795V9V8f4urlxaUZNm+aSwsbHuAIDKdt26U/UcOjnBX1jZrnMT0MfHengKmfcxR7CqQ//p/oqjJV3zh/u9NjnMje/kmBO3jHs9shWCQICEI+ExFFqrn4RV3KxJD3UdHXMl4mRHsZxaFQRAYZPGlUtz49MX/Jz3+ZzYwQSyr9H9bn5gOYLiO7Nb3tpZiqL4mqeTHknyur++eyecSuOtgU0nvzIpdGKCJwSB6g6dxY4Rltue3DYxl7Zqdky8n4BMgv0kbBGXRjRXNFiR5duKLTbEYkdvb841guKf7q/65lD1Pw6MszrQ0lbN3J9ylm687CNiHn4zc0aat5NjTvxrpFlfUEjw4tFBVR06KhlyoJhKb5P1mAVsmhufUdOpn5Pht2pfZYK/i7eIZXWgOy+2UMlwTp2qsKmnTW2O8eE/FOXmJ76FVBKl3lot050sk0d580dHX3c6Wb3csOZ4/a6cVh6T8vkTsXOH+bH+/WPanbi/+D93UkeijNcp+wAAAABJRU5ErkJggg=="

def logout_user():
    """Sign out the current user and clear only client-side session state."""
    if supabase:
        try:
            supabase.auth.sign_out()
        except Exception:
            pass
    st.session_state.user = None
    st.session_state.session = None
    st.session_state.sorulan_ids = []
    st.session_state.puanlar = []
    st.session_state.mevcut_soru = None
    st.session_state.son_analiz = None
    st.session_state.last_processed_audio = None
    st.rerun()

def render_pilotprep_header(show_logout=False):
    # Keep the shared brand header free of a second logout control.
    # The existing sidebar logout button remains the single sign-out entry point.
    st.markdown(f"""
    <div class="pilotprep-topbar">
      <div class="pilotprep-brand-group">
        <div class="pilotprep-wordmark">
          <span class="pilotprep-mark">✈</span>
          <span>Pilot<span class="prep">Prep</span></span>
        </div>
        <img class="icao-logo" src="{_ICAO_LOGO_DATA_URI}" alt="ICAO logo">
      </div>
    </div>
    """, unsafe_allow_html=True)

# --- LOGIN / SIGN-UP SCREEN ---
render_pilotprep_header(show_logout=bool(st.session_state.user))
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
        <div class="title">✈️ PilotPrep</div>
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
    <div class="name">✈️ Pilot<span>Prep</span></div>
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

if st.sidebar.button("Log out", use_container_width=True, key="sidebar_logout"):
    logout_user()

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
    <div class="plane"><svg viewBox="0 0 120 44" aria-hidden="true"><path fill="#fff" d="M4 24 Q4 19 14 19 L92 19 Q113 20 117 24 Q113 28 92 29 L14 29 Q4 29 4 24Z"/><path fill="#fff" d="M12 19 L3 5 L16 5 L30 19Z"/><path fill="#fff" d="M50 27 L72 41 L84 41 L70 27Z"/><path fill="#fff" opacity=".7" d="M52 20 L70 9 L80 9 L68 20Z"/><circle cx="100" cy="23.5" r="1.6" fill="#0A1626"/><circle cx="92" cy="23.5" r="1.6" fill="#0A1626"/><circle cx="84" cy="23.5" r="1.6" fill="#0A1626"/></svg></div>
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
      .card{background:#0A1626;border-radius:12px;padding:16px 18px;color:#fff;display:flex;align-items:center;gap:18px;flex-wrap:wrap;box-sizing:border-box;}
      .adi{width:104px;height:104px;flex-shrink:0;}
      .horizon{transform-origin:60px 60px;animation:bank 11s ease-in-out infinite alternate;}
      @keyframes bank{from{transform:rotate(-4deg) translateY(-3px);}to{transform:rotate(5deg) translateY(4px);}}
      .clk{min-width:120px;}
      .row{margin-bottom:8px;}
      .lab{color:#8FA8C8;font-size:12px;font-weight:500;}
      .t{font-size:26px;font-weight:600;line-height:1.05;font-variant-numeric:tabular-nums;}
      .t.utc{color:#F2A81D;}
      @media (prefers-reduced-motion: reduce){.horizon{animation:none;}}
    

    /* ---------- Flight-deck refinement: visual-only overrides ---------- */
    :root {
        --paper: #1B2A3B;
        --panel: #142337;
        --panel-2: #172B42;
        --card: #10233A;
        --panel-line: #304761;
        --line: #304761;
        --ink: #F0F5FC;
        --ink-soft: #B2C1D4;
    }

    .stApp {
        background:
            radial-gradient(ellipse at 55% 0%, rgba(86, 119, 157, .10), transparent 46%),
            #1B2A3B !important;
        color: #F0F5FC !important;
    }
    [data-testid="stMain"],
    [data-testid="stMainBlockContainer"] {
        background: transparent !important;
    }
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #142337 0%, #101D2D 100%) !important;
        border-right: 1px solid #304761 !important;
    }

    .hero {
        background:
            linear-gradient(105deg, rgba(12, 29, 49, .98) 0%, rgba(17, 42, 68, .96) 62%, rgba(24, 48, 73, .93) 100%) !important;
        border-color: #3A5572 !important;
        box-shadow: 0 8px 22px rgba(3, 10, 20, .16), inset 0 1px rgba(255,255,255,.025) !important;
    }
    .hero::after {
        background: repeating-linear-gradient(90deg, transparent 0 43px, rgba(164, 190, 220, .028) 44px 45px) !important;
    }
    .hero .sub, .hero .hi { color: #B8C9DD !important; }

    .strip {
        background: #13263B !important;
        border-color: #304761 !important;
        box-shadow: 0 5px 14px rgba(3, 10, 20, .10) !important;
    }
    .strip .cell { border-right-color: #304761 !important; }
    .strip .cell:hover { background: rgba(255,255,255,.025) !important; }
    .strip .k { color: #B2C1D4 !important; }
    .strip .v { color: #F0F5FC !important; }

    .brief, .st-key-mic_card, .report, .flight, .tip, .model-answer {
        background: #11243A !important;
        border-color: #304761 !important;
        box-shadow: 0 6px 16px rgba(3, 10, 20, .12) !important;
        color: #F0F5FC !important;
    }
    .brief { border-left-color: #F0B43B !important; }
    .brief:hover {
        transform: none !important;
        box-shadow: 0 7px 17px rgba(3, 10, 20, .14) !important;
    }
    .q-text, .mic-h, .flight .h, .flight .pct, .flight .note b,
    .stTextArea label p, .verdict .label, .chips-title, .tip b {
        color: #F0F5FC !important;
    }
    .mic-s, .flight .legend, .flight .note, .verdict .desc,
    .chips-title, .tip { color: #B2C1D4 !important; }

    .stTextArea textarea, .stTextInput input {
        background: #0E2034 !important;
        color: #F0F5FC !important;
        border-color: #3A5572 !important;
    }
    .stTextArea textarea::placeholder, .stTextInput input::placeholder {
        color: #9AAFC8 !important;
    }
    .stTextArea textarea:focus, .stTextInput input:focus {
        border-color: #58BFE8 !important;
        box-shadow: 0 0 0 2px rgba(88,191,232,.10) !important;
    }

    .stButton button {
        transition: background-color .15s ease, border-color .15s ease !important;
    }
    .stButton button:hover {
        transform: none !important;
        box-shadow: 0 4px 12px rgba(3,10,20,.16) !important;
    }
    .stButton button[kind="primary"],
    .stButton button[data-testid="stBaseButton-primary"] {
        background: linear-gradient(135deg, #F6BE4D, #EBAA2D) !important;
        border-color: #F0B43B !important;
        box-shadow: 0 3px 10px rgba(235,170,45,.10) !important;
    }
    .stButton button[kind="secondary"],
    .stButton button[data-testid="stBaseButton-secondary"] {
        background: #172E48 !important;
        color: #E7EFFA !important;
        border-color: #3A5572 !important;
    }

    .st-key-mic_card button {
        box-shadow: 0 0 0 5px rgba(53,189,245,.075),
                    0 5px 14px rgba(8,30,60,.22),
                    inset 0 2px 8px rgba(255,255,255,.16) !important;
    }
    .st-key-mic_card button:hover {
        transform: scale(1.02) !important;
        box-shadow: 0 0 0 6px rgba(53,189,245,.09),
                    0 6px 16px rgba(8,30,60,.24) !important;
    }
    .hero .plane { opacity: .30 !important; }
    .hero .cloud { opacity: .34 !important; }
    .flight .track { background: #304761 !important; }
    .report::before { background: #1A3049 !important; color: #B2C1D4 !important; }

</style></head><body>
    <div class="card">
      <svg class="adi" viewBox="0 0 120 120" aria-hidden="true">
        <defs><clipPath id="c"><circle cx="60" cy="60" r="52"/></clipPath></defs>
        <g clip-path="url(#c)"><g class="horizon">
          <rect x="-60" y="-60" width="240" height="120" fill="#3C7DD9"/>
          <rect x="-60" y="60" width="240" height="120" fill="#7A5230"/>
          <line x1="-60" y1="60" x2="180" y2="60" stroke="#fff" stroke-width="1.5"/>
          <line x1="46" y1="48" x2="74" y2="48" stroke="#fff" stroke-width="1" opacity=".7"/>
          <line x1="52" y1="36" x2="68" y2="36" stroke="#fff" stroke-width="1" opacity=".7"/>
          <line x1="46" y1="72" x2="74" y2="72" stroke="#fff" stroke-width="1" opacity=".7"/>
          <line x1="52" y1="84" x2="68" y2="84" stroke="#fff" stroke-width="1" opacity=".7"/>
        </g></g>
        <circle cx="60" cy="60" r="52" fill="none" stroke="#223A5A" stroke-width="5"/>
        <path d="M60 4 L56 12 L64 12Z" fill="#F2A81D"/>
        <path d="M28 62 H48 L52 66 M92 62 H72 L68 66" fill="none" stroke="#F2A81D" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round"/>
        <circle cx="60" cy="62" r="3" fill="#F2A81D"/>
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
