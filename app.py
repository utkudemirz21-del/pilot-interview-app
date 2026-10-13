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


# --- CANLI KONUŞMA TANIMA (ses dosyası kaydetmeden) ---
@st.cache_resource
def _live_speech_component():
    component_dir = Path(tempfile.gettempdir()) / "pilotinterviewpro_live_speech_component"
    component_dir.mkdir(parents=True, exist_ok=True)
    html_path = component_dir / "index.html"
    html_path.write_text(r"""<!doctype html>
<html lang="tr">
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
  <button id="mic" class="mic" aria-label="Mikrofonu başlat" title="Konuşmayı başlat">🎙</button>
  <div class="texts">
    <div class="title">Canlı sesli yanıt</div>
    <div id="status" class="status">Başlamak için mikrofona dokunun. Konuşmanız anlık olarak yazıya çevrilir.</div>
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
    mic.setAttribute('aria-label','Mikrofonu başlat');
    mic.title = 'Konuşmayı başlat';
    try { if (recognition) recognition.stop(); } catch(e) {}
    setStatus('Konuşma durduruldu. Metin yanıt kutusuna aktarıldı.');
  }
  function start() {
    if (!SpeechRecognition) {
      setStatus('Bu tarayıcı canlı konuşma tanımayı desteklemiyor. Güncel Chrome kullanın.');
      return;
    }
    finalText = '';
    lastSent = '';
    recognition = new SpeechRecognition();
    recognition.lang = 'tr-TR';
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.maxAlternatives = 1;
    recognition.onstart = () => {
      active = true;
      mic.classList.add('live');
      mic.setAttribute('aria-label','Mikrofonu durdur');
      mic.title = 'Konuşmayı durdur';
      setStatus('Dinleniyor… Konuştukça metin güncellenir.', true);
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
      setStatus(current ? current : 'Dinleniyor…', true);
    };
    recognition.onerror = (event) => {
      if (event.error === 'not-allowed' || event.error === 'service-not-allowed') {
        setStatus('Mikrofon izni verilmedi. Tarayıcı izinlerinden mikrofona izin verin.');
      } else if (event.error !== 'no-speech' && event.error !== 'aborted') {
        setStatus('Konuşma tanıma hatası: ' + event.error);
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
    catch(e) { setStatus('Mikrofon başlatılamadı. Sayfayı yenileyip tekrar deneyin.'); }
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


# Sayfa Yapılandırması
st.set_page_config(
    page_title="PilotInterviewPro",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- SUPABASE BAĞLANTISI VE OTURUM YÖNETİMİ ---
@st.cache_resource
def init_supabase() -> Client:
    url = st.secrets.get("SUPABASE_URL", "")
    key = st.secrets.get("SUPABASE_KEY", "")
    if not url or not key:
        return None
    return create_client(url, key)

supabase = init_supabase()

# 🎨 TASARIM SİSTEMİ — "Flight Deck"
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

    /* ---------- Yan panel (kokpit paneli) ---------- */
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

    /* ---------- Enstrüman şeridi (özet metrikler) ---------- */
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

    /* ---------- Soru kartı (briefing) ---------- */
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
    .tag-diff.kolay { color:#13795B; border-color:#9ADBC4; background:#EAF8F2; }
    .tag-diff.orta  { color:#8A5B00; border-color:#F2D18A; background:#FEF6E1; }
    .tag-diff.zor   { color:#A82F28; border-color:#EFB1AC; background:#FDEEEC; }
    .q-text { font-family:'Barlow Semi Condensed',sans-serif; font-size: 2.1rem !important; font-weight: 700 !important; color: var(--ink); line-height: 1.35; max-width: 100%; }

    /* ---------- Mikrofon paneli ---------- */
    .st-key-mic_card {
        background: var(--card);
        border: 1px solid var(--line);
        border-radius: 12px;
        padding: 18px 22px 8px 22px;
        margin-bottom: 18px;
    }
    .mic-h { font-family:'Barlow Semi Condensed',sans-serif; font-weight:600; font-size:1.15rem; color:var(--ink); }
    .mic-s { color: var(--ink-soft); font-size: 0.88rem; margin: 2px 0 10px 0; }

    /* ---------- Form elemanları ---------- */
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

    /* ---------- Karne (skor göstergesi) ---------- */
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

    /* ---------- İpucu ---------- */
    .tip {
        background: transparent; border: 1px dashed #B5C0CF; border-radius: 12px;
        padding: 16px 22px; color: var(--ink-soft); font-size: 0.92rem; line-height: 1.6;
    }
    .tip b { color: var(--ink); }

    /* ---------- Uçuş ilerlemesi ---------- */
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

    /* ---------- Hareket ---------- */
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
    .tag-diff.kolay { color: #65E7C1 !important; border-color: #226C65 !important; background: #0C393B !important; }
    .tag-diff.orta { color: #FFD16A !important; border-color: #745B29 !important; background: #3A2D17 !important; }
    .tag-diff.zor { color: #FF9DA6 !important; border-color: #783D4A !important; background: #3A1E2B !important; }
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
    button[aria-label*="Mikrofon"],
    button[title*="Mikrofon"] {
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
    button[aria-label*="Mikrofon"] svg,
    button[title*="Mikrofon"] svg {
        color: #FFFFFF !important;
        fill: currentColor !important;
        stroke: currentColor !important;
    }
    .st-key-mic_card button:hover,
    button[aria-label*="Mikrofon"]:hover,
    button[title*="Mikrofon"]:hover {
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
      radial-gradient(ellipse at 80% 5%, rgba(110,202,255,.24), transparent 38%),
      linear-gradient(125deg, #EAF6FF 0%, #D7EEFF 43%, #B8E0FF 100%) !important;
    border: 1px solid #9BCDF5 !important;
    border-radius: 28px !important;
    color: #102C4B !important;
    box-shadow: 0 18px 48px rgba(35,116,180,.16), inset 0 1px rgba(255,255,255,.8) !important;
    animation: login-arrive .7s ease-out both;
}
.login-hero .title { color:#102C4B !important; font-size:clamp(2rem,4vw,3.2rem) !important; position:relative; z-index:2; }
.login-hero .sub { color:#416582 !important; position:relative; z-index:2; }
.login-kicker { display:inline-flex; align-items:center; gap:8px; color:#28618C; font-size:11px; font-weight:800; letter-spacing:.14em; margin-bottom:9px; position:relative; z-index:2; }
.live-dot { width:8px; height:8px; background:#19B99A; border-radius:50%; box-shadow:0 0 0 4px rgba(25,185,154,.13); animation: dot-beat 1.8s ease-in-out infinite; }
.login-orbit { position:absolute; width:230px; height:150px; right:5%; top:7px; opacity:.72; pointer-events:none; }
.orbit-ring { position:absolute; border:1px solid rgba(39,117,177,.35); border-radius:50%; transform:rotate(-18deg); }
.ring-a { width:210px;height:76px;top:22px;left:5px; }
.ring-b { width:160px;height:115px;top:3px;left:30px;transform:rotate(38deg); }
.orbit-plane { position:absolute; left:98px;top:48px;font-size:34px;color:#287FC0;filter:drop-shadow(0 4px 6px rgba(40,127,192,.22));animation: plane-float 4.5s ease-in-out infinite; }
.orbit-dot { position:absolute;width:7px;height:7px;background:#F5A623;border-radius:50%;box-shadow:0 0 0 5px rgba(245,166,35,.13); }
.dot-a { left:29px;top:56px;animation: dot-beat 2.2s infinite; }
.dot-b { right:12px;top:94px;background:#19B99A;animation: dot-beat 1.7s infinite .4s; }
.login-widgets { display:flex;justify-content:center;gap:10px;flex-wrap:wrap;margin-top:22px;position:relative;z-index:2; }
.login-widget { display:flex;align-items:center;gap:10px;min-width:190px;text-align:left;padding:10px 13px;background:rgba(255,255,255,.58);border:1px solid rgba(93,155,202,.30);border-radius:15px;backdrop-filter:blur(8px);box-shadow:0 5px 15px rgba(47,116,168,.06);animation: widget-up .6s ease-out both; }
.login-widget:nth-child(2) { animation-delay:.12s; }
.login-widget:nth-child(3) { animation-delay:.24s; }
.widget-icon { width:31px;height:31px;display:grid;place-items:center;border-radius:10px;background:#D2EBFF;color:#176AA8;font-size:19px;font-weight:800; }
.login-widget b { display:block;font-size:12px;color:#173E60;font-weight:800; }
.login-widget small { display:block;font-size:10px;color:#587894;margin-top:2px; }
.widget-pulse { width:8px;height:8px;margin-left:auto;background:#18B99A;border-radius:50%;box-shadow:0 0 0 4px rgba(24,185,154,.12);animation:dot-beat 1.8s infinite; }
.mini-bars { margin-left:auto;height:23px;display:flex;align-items:end;gap:3px; }
.mini-bars i { width:4px;border-radius:4px;background:#278DD0;animation:bar-bounce 1s ease-in-out infinite alternate; }
.mini-bars i:nth-child(1){height:8px}.mini-bars i:nth-child(2){height:16px;animation-delay:.2s}.mini-bars i:nth-child(3){height:12px;animation-delay:.35s}.mini-bars i:nth-child(4){height:22px;animation-delay:.1s}.mini-bars i:nth-child(5){height:10px;animation-delay:.4s}
.widget-check { margin-left:auto;display:grid;place-items:center;width:23px;height:23px;border-radius:50%;background:#D3F8EF;color:#078B76;font-weight:900; }
div[data-testid="stTabs"] { margin-top: 8px; }
div[data-testid="stTabs"] [role="tablist"] { background:#DCEFFF !important;border:1px solid #B7D9F4 !important;border-radius:16px !important;padding:5px !important;gap:5px !important; }
div[data-testid="stTabs"] button[role="tab"] { border-radius:12px !important;color:#426582 !important;font-weight:750 !important;transition:all .2s ease !important; }
div[data-testid="stTabs"] button[role="tab"][aria-selected="true"] { background:#FFFFFF !important;color:#155A91 !important;box-shadow:0 3px 10px rgba(26,91,143,.12) !important; }
div[data-testid="stTabs"] button[role="tab"] p { color:inherit !important;font-weight:800 !important; }
div[data-testid="stTextInput"] { margin-bottom:12px; }
div[data-testid="stTextInput"] label, div[data-testid="stTextInput"] label p { color:#BFDFFF !important;font-size:13px !important;font-weight:800 !important; }
div[data-testid="stTextInput"] input {
    height:50px !important;box-sizing:border-box !important;
    background:#F7FBFF !important;color:#142D48 !important;
    -webkit-text-fill-color:#142D48 !important;
    border:1.5px solid #A9CBE8 !important;border-radius:14px !important;
    padding:0 15px !important;box-shadow:0 4px 14px rgba(0,0,0,.08) !important;
    caret-color:#176AA8 !important;
}
div[data-testid="stTextInput"] input::placeholder { color:#7893AA !important;opacity:1 !important; }
div[data-testid="stTextInput"] input:focus { border-color:#4DADEB !important;box-shadow:0 0 0 4px rgba(77,173,235,.18) !important; }
div[data-testid="stTextInput"] [data-baseweb="input"] { background:#F7FBFF !important;border-radius:14px !important; }
div[data-testid="stTextInput"] [data-baseweb="input"] > div { background:transparent !important; }
div[data-testid="stTextInput"] button { color:#254967 !important; }
div[data-testid="stButton"] button[kind="primary"] { min-height:49px !important;border-radius:14px !important;font-weight:800 !important;letter-spacing:.01em; }

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

</style>
""", unsafe_allow_html=True)

# Helper Fonksiyonlar
def turkish_lower(text: str) -> str:
    if not text: return ""
    rep = {'I': 'ı', 'İ': 'i', 'Ç': 'ç', 'Ş': 'ş', 'Ğ': 'ğ', 'Ü': 'ü', 'Ö': 'ö'}
    for search, replace in rep.items(): text = text.replace(search, replace)
    return text.lower()

def transcribe_audio(audio_bytes):
    recognizer = sr.Recognizer()
    try:
        audio_file = io.BytesIO(audio_bytes)
        with sr.AudioFile(audio_file) as source:
            audio_data = recognizer.record(source)
            return recognizer.recognize_google(audio_data, language="tr-TR")
    except Exception:
        return ""

def is_flexible_match(keyword: str, clean_answer: str) -> bool:
    clean_kw = turkish_lower(str(keyword).strip())
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
    clean_answer = re.sub(r'[^\w\s]', ' ', turkish_lower(user_answer))
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

# Session State Başlatma
if "user" not in st.session_state: st.session_state.user = None
if "session" not in st.session_state: st.session_state.session = None
if "sorulan_ids" not in st.session_state: st.session_state.sorulan_ids = []
if "puanlar" not in st.session_state: st.session_state.puanlar = []
if "mevcut_soru" not in st.session_state: st.session_state.mevcut_soru = None
if "son_analiz" not in st.session_state: st.session_state.son_analiz = None
if "secilen_kategori" not in st.session_state: st.session_state.secilen_kategori = "Tüm Kategoriler"
if "last_processed_audio" not in st.session_state: st.session_state.last_processed_audio = None

# SUPABASE KONTROLÜ VE OTURUMU GERİ YÜKLEME
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

# --- GÖRSEL YARDIMCILAR (sadece UI) ---
SKOR_BILGI = {
    100: ("Mükemmel", "#2FBF8F", "Yanıtınız beklenen cevapla tam uyumlu. Bu seviyeyi koruyun."),
    80:  ("Çok iyi", "#2FBF8F", "Yanıtınız büyük oranda yeterli. Eksik kalan kavramları ekleyerek 100'e çıkabilirsiniz."),
    60:  ("Orta seviye", "#F2A81D", "Temel fikir var ancak bazı önemli detaylar eksik kaldı."),
    30:  ("Zayıf", "#D8483F", "Doğru yanıttan uzak kalındı. Örnek cevabı okuyup tekrar deneyin."),
    0:   ("Yetersiz", "#D8483F", "Hedeflenen açıklamalar yanıtınızda bulunamadı."),
}

def gauge_svg(puan: int, renk: str) -> str:
    uzunluk = 251.33
    dolu = uzunluk * (puan / 100)
    return f"""
    <svg viewBox="0 0 200 124" role="img" aria-label="Skor {puan} / 100">
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

# --- GİRİŞ / KAYIT EKRANI ---
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
        <div class="sub">Havayolu mülakatına teknik sorularla hazırlanın. İlerlemeniz hesabınızda saklanır.</div>
        <div class="login-widgets">
            <div class="login-widget"><span class="widget-icon">◉</span><span><b>Canlı pratik</b><small>Konuşarak yanıtlayın</small></span><i class="widget-pulse"></i></div>
            <div class="login-widget"><span class="widget-icon">⌁</span><span><b>Uçuş göstergeleri</b><small>İlerlemenizi takip edin</small></span><span class="mini-bars"><i></i><i></i><i></i><i></i><i></i></span></div>
            <div class="login-widget"><span class="widget-icon">✦</span><span><b>Akıllı değerlendirme</b><small>Yanıtınıza geri bildirim</small></span><span class="widget-check">✓</span></div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    col_auth1, col_auth2, col_auth3 = st.columns([1, 1.7, 1])
    with col_auth2:
        tab_login, tab_signup = st.tabs(["Giriş yap", "Kayıt ol"])

        with tab_login:
            login_email = st.text_input("E-posta", key="l_email")
            login_pass = st.text_input("Şifre", type="password", key="l_pass")
            if st.button("Giriş yap", type="primary", use_container_width=True):
                if supabase:
                    try:
                        res = supabase.auth.sign_in_with_password({"email": login_email, "password": login_pass})
                        st.session_state.user = res.user
                        st.session_state.session = res.session
                        load_user_progress()
                        st.success("Giriş başarılı!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Giriş hatası: {e}")
                else:
                    st.error("Supabase bağlantı bilgileri eksik (Secrets).")

        with tab_signup:
            signup_email = st.text_input("E-posta", key="s_email")
            signup_pass = st.text_input("Şifre (en az 6 karakter)", type="password", key="s_pass")
            if st.button("Hesap oluştur", use_container_width=True):
                if supabase:
                    try:
                        res = supabase.auth.sign_up({"email": signup_email, "password": signup_pass})
                        st.session_state.user = res.user
                        st.session_state.session = res.session
                        save_user_progress()
                        st.success("Hesabınız oluşturuldu!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Kayıt hatası: {e}")
    st.stop()

# Oturum Açık ise İlerlemeyi Yükle (İlk Yüklemede)
if st.session_state.user and not st.session_state.sorulan_ids and not st.session_state.puanlar:
    load_user_progress()

# --- GİRİŞ YAPILDIKTAN SONRAKİ UYGULAMA AKIŞI ---

def yeni_soru_getir(kategori_filtresi):
    if kategori_filtresi == "Tüm Kategoriler":
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

# Hesaplamalar
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

kategoriler = ["Tüm Kategoriler"] + sorted(list(set(q["category"] for q in questions_data))) if questions_data else []

def on_kategori_change():
    yeni_kat = st.session_state.kat_select_box
    st.session_state.secilen_kategori = yeni_kat
    yeni_soru_getir(yeni_kat)

kat_index = kategoriler.index(st.session_state.secilen_kategori) if st.session_state.secilen_kategori in kategoriler else 0

secilen_kategori = st.sidebar.selectbox("Mülakat kategorisi", kategoriler, index=kat_index, key="kat_select_box", on_change=on_kategori_change)

st.sidebar.markdown(f"""
<div style="margin-top:14px;">
    <div class="side-stat"><span>Yanıtlanan</span><b>{tamamlanan}</b></div>
    <div class="side-stat"><span>Ortalama skor</span><b>%{ort_skor:.0f}</b></div>
    <div class="side-stat"><span>Hedef</span><b>%80+</b></div>
</div>
""", unsafe_allow_html=True)

st.sidebar.markdown("<div style='height:18px'></div>", unsafe_allow_html=True)

if st.sidebar.button("İlerlemeyi sıfırla", use_container_width=True, help="Tüm yanıt ve puan geçmişinizi sıfırlar."):
    reset_user_progress()
    st.rerun()

st.sidebar.markdown("""
<div class="radar"><span class="blip b1"></span><span class="blip b2"></span></div>
""", unsafe_allow_html=True)

if st.sidebar.button("Çıkış yap", use_container_width=True):
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

# Kullanıcı adı
def display_name(email: str) -> str:
    local = (email or "").split("@")[0]
    words = [w for w in re.split(r"[._\-\s]+", local) if w]
    out = []
    for w in words:
        first = "İ" if w[0] == "i" else ("I" if w[0] == "ı" else w[0].upper())
        out.append(first + turkish_lower(w[1:]))
    return " ".join(out) if out else "Pilot Adayı"

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
            <div class="hi">Hoş geldiniz</div>
            <div class="name">{kullanici_adi_html}</div>
        </div>
    </div>
    <div class="title">Pilot mülakatına hazırlanın</div>
    <div class="sub">Teknik sorulara sesle yanıt verin, havacılık terminolojisini net kullanın. İlerlemeniz hesabınıza otomatik kaydedilir.</div>
</div>
""", unsafe_allow_html=True)

# Enstrüman şeridi
st.markdown(f"""
<div class="strip">
    <div class="cell"><div class="k">Toplam soru</div><div class="v">{toplam_soru}</div></div>
    <div class="cell"><div class="k">Kategori</div><div class="v">{max(len(kategoriler)-1, 0)}</div></div>
    <div class="cell"><div class="k">Ortalama skor</div><div class="v">%{ort_skor:.0f}</div></div>
    <div class="cell"><div class="k">Hedef skor</div><div class="v">%80<small>ve üzeri</small></div></div>
</div>
""", unsafe_allow_html=True)

col_left, col_right = st.columns([2.5, 1], gap="large")

with col_left:
    if st.session_state.mevcut_soru:
        soru = st.session_state.mevcut_soru
        input_key = f"answer_input_{soru.get('id')}"

        zorluk = str(soru.get('difficulty', 'Orta'))
        zorluk_css = {"Kolay": "kolay", "Orta": "orta", "Zor": "zor"}.get(zorluk, "orta")
        kategori_html = html.escape(str(soru.get('category', 'Genel')))
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
            model_answer_text = "Bu soru için mülakatta açıklanması beklenen temel konu: " + ", ".join(kw_list) + " kavramlarının doğru usullerle ifade edilmesidir."

        with st.container(key="mic_card"):
            st.markdown("""
            <div class="mic-h">Sesli yanıt</div>
            <div class="mic-s">Mikrofonu açıp konuşun. Söyledikleriniz eş zamanlı olarak metne aktarılır; ses dosyası kaydedilmez.</div>
            """, unsafe_allow_html=True)
            live_text = live_speech_input(
                key=f"live_{soru.get('id')}_{len(st.session_state.sorulan_ids)}",
                default=""
            )
            if isinstance(live_text, str) and live_text.strip():
                st.session_state[input_key] = live_text

        kullanici_cevabi = st.text_area("Algılanan / yazılan yanıtınız", placeholder="Mikrofonda konuştukça metin burada belirir. İsterseniz elle de düzenleyebilirsiniz.", height=130, key=input_key)

        btn_c1, btn_c2 = st.columns([1, 1])
        with btn_c1:
            if st.button("Yanıtı değerlendir", type="primary", use_container_width=True):
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
                    st.warning("Önce bir yanıt söyleyin veya yazın.")

        with btn_c2:
            if st.button("Sonraki soru", use_container_width=True):
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
                kw_html += f'<div class="chips-title">Yanıtınızda geçen kavramlar</div><div class="chips">{chips_html(matched, "ok")}</div>'
            if missing:
                kw_html += f'<div class="chips-title">Eklenebilecek kavramlar</div><div class="chips">{chips_html(missing, "miss")}</div>'

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
                <div class="h">Mülakatta beklenen örnek cevap</div>
                <div class="t">{model_answer_html}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("""
    <div class="tip">
        <b>Mülakat ipucu:</b> Sistemlerin çalışmasını anlatırken <b>neden-sonuç ilişkisini</b> ve standart operasyon usullerini (SOP) vurgulamak puanınızı artırır.
    </div>
    """, unsafe_allow_html=True)

with col_right:
    yuzde = min(int((tamamlanan / toplam_soru) * 100), 100) if toplam_soru > 0 else 0
    st.markdown(f"""
    <div class="flight">
        <div class="h">Uçuş ilerlemesi</div>
        <div class="pct">%{yuzde}</div>
        <div class="track">
            <div class="fill" style="width:{yuzde}%;"></div>
            <div class="dot" style="left:{yuzde}%;"></div>
            <div class="end"></div>
        </div>
        <div class="legend"><span>Kalkış</span><span>Varış</span></div>
        <div class="note">Toplam <b>{toplam_soru}</b> sorudan <b>{tamamlanan}</b> tanesi yanıtlandı.</div>
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
        <div class="row" style="margin-bottom:0"><div class="lab">Türkiye saati</div><div class="t" id="l">--:--:--</div></div>
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
