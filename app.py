import json
import random
import re
import streamlit as st
import streamlit.components.v1 as components

# Sayfa Yapılandırması
st.set_page_config(
    page_title="PilotInterviewPro",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS Tasarımı
st.markdown("""
<style>
    .stApp { background-color: #f8fafc !important; color: #0f172a !important; }
    section[data-testid="stSidebar"] { background-color: #0b2559 !important; }
    section[data-testid="stSidebar"] label { color: #ffffff !important; font-weight: 700 !important; }
    
    .hero-banner {
        background: linear-gradient(135deg, rgba(11, 37, 89, 0.95) 0%, rgba(29, 78, 216, 0.85) 100%);
        border-radius: 16px; padding: 32px; color: #ffffff !important; margin-bottom: 24px;
    }
    .hero-title { font-size: 2rem; font-weight: 700; }
    .hero-subtitle { font-size: 1rem; color: #e2e8f0 !important; }

    .main-card {
        background: #ffffff !important; border-radius: 16px;
        border: 1px solid #e2e8f0; padding: 24px; margin-bottom: 16px;
    }
    .question-title { font-size: 1.25rem; font-weight: 700; color: #0f172a !important; margin-top: 12px; }
    
    .badge-category {
        background-color: #dbeafe !important; color: #1e40af !important;
        border: 1.5px solid #93c5fd !important; padding: 6px 14px; border-radius: 20px; font-weight: 800;
    }
    .badge-difficulty {
        background-color: #e2e8f0 !important; color: #1e293b !important;
        border: 1.5px solid #cbd5e1 !important; padding: 6px 14px; border-radius: 20px; font-weight: 800; margin-left: 8px;
    }

    .stTextArea textarea {
        background-color: #ffffff !important; color: #0f172a !important;
        border: 1.5px solid #cbd5e1 !important; border-radius: 12px !important; padding: 14px !important;
    }
    
    .side-card {
        background: #ffffff !important; border-radius: 16px;
        border: 1px solid #e2e8f0; padding: 20px; margin-bottom: 16px;
    }
    .progress-percent { font-size: 2.2rem; font-weight: 800; color: #2563eb !important; }
</style>
""", unsafe_allow_html=True)

# 🛠️ TÜRKÇE MÜKEMMEL HARF DÖNÜŞTÜRÜCÜ
def turkish_lower(text: str) -> str:
    if not text:
        return ""
    rep = {'I': 'ı', 'İ': 'i', 'Ç': 'ç', 'Ş': 'ş', 'Ğ': 'ğ', 'Ü': 'ü', 'Ö': 'ö'}
    for search, replace in rep.items():
        text = text.replace(search, replace)
    return text.lower()

# 🛠️ KELİME TARAMA VE PUANLAMA MOTORU
def calculate_score(user_answer: str, keywords: list) -> dict:
    if not user_answer or not user_answer.strip():
        return {
            "score": 0,
            "matched_count": 0,
            "matched_keywords": [],
            "missing_keywords": keywords
        }

    clean_answer = turkish_lower(user_answer)
    clean_answer = re.sub(r'[^\w\s]', ' ', clean_answer)

    matched_keywords = []
    missing_keywords = []

    for kw in keywords:
        clean_kw = turkish_lower(str(kw).strip())
        if clean_kw and clean_kw in clean_answer:
            matched_keywords.append(kw)
        else:
            missing_keywords.append(kw)

    match_count = len(matched_keywords)

    if match_count >= 4:
        score = 100
    elif match_count == 3:
        score = 80
    elif match_count == 2:
        score = 60
    elif match_count == 1:
        score = 30
    else:
        score = 0

    return {
        "score": score,
        "matched_count": match_count,
        "matched_keywords": matched_keywords,
        "missing_keywords": missing_keywords
    }

# JSON Verisini Yükle
@st.cache_data(ttl=60)
def load_questions():
    try:
        with open("questions.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        st.error(f"Soru dosyası yüklenemedi: {e}")
        return []

questions_data = load_questions()

# Session State
if "sorulan_ids" not in st.session_state:
    st.session_state.sorulan_ids = []
if "mevcut_soru" not in st.session_state:
    st.session_state.mevcut_soru = None
if "puanlar" not in st.session_state:
    st.session_state.puanlar = []
if "son_analiz" not in st.session_state:
    st.session_state.son_analiz = None
if "secilen_kategori" not in st.session_state:
    st.session_state.secilen_kategori = "Tüm Kategoriler"

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

# Sol Menü (Sidebar)
st.sidebar.markdown("""
<div style="padding: 10px 0 15px 0;">
    <h2 style="color: #ffffff; margin:0; font-size: 1.4rem;">✈️ PilotInterviewPro</h2>
    <p style="color: #93c5fd; font-size: 0.8rem; margin-top:2px;">Practice.
