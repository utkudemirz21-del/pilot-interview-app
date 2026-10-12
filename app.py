import json
import random
import re
import io
import streamlit as st
import speech_recognition as sr
from audio_recorder_streamlit import audio_recorder

# Sayfa Yapılandırması
st.set_page_config(
    page_title="PilotInterviewPro",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 🎨 MODERN VE ŞIK UI & ANİMASYON CSS KODLARI
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

    * {
        font-family: 'Inter', sans-serif;
    }

    .stApp { 
        background-color: #f1f5f9 !important; 
        color: #0f172a !important; 
    }
    
    @keyframes fadeInUp {
        from {
            opacity: 0;
            transform: translateY(18px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }

    .animated-element {
        animation: fadeInUp 0.5s cubic-bezier(0.16, 1, 0.3, 1) forwards;
    }

    section[data-testid="stSidebar"] { 
        background-color: #0b1e36 !important; 
        border-right: 1px solid #1e293b;
    }
    section[data-testid="stSidebar"] label { 
        color: #f8fafc !important; 
        font-weight: 600 !important; 
    }

    div[data-baseweb="select"] {
        background-color: #ffffff !important;
        border-radius: 8px !important;
    }
    div[data-baseweb="select"] * {
        color: #0f172a !important;
        font-weight: 700 !important;
    }

    .hero-banner {
        background: linear-gradient(135deg, #0b2559 0%, #1d4ed8 50%, #3b82f6 100%);
        border-radius: 20px; 
        padding: 36px; 
        color: #ffffff !important; 
        margin-bottom: 24px;
        box-shadow: 0 10px 25px -5px rgba(29, 78, 216, 0.25);
        transition: transform 0.3s ease;
    }
    .hero-banner:hover {
        transform: translateY(-2px);
    }
    .hero-title { font-size: 2.2rem; font-weight: 800; letter-spacing: -0.5px; }
    .hero-subtitle { font-size: 1.05rem; color: #e2e8f0 !important; margin-top: 6px; }

    .main-card {
        background: #ffffff !important; 
        border-radius: 20px;
        border: 1px solid #e2e8f0; 
        padding: 28px; 
        margin-bottom: 20px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.03);
        transition: all 0.3s ease;
    }
    .main-card:hover {
        box-shadow: 0 10px 25px rgba(0,0,0,0.06);
        border-color: #cbd5e1;
    }
    .question-title { 
        font-size: 1.35rem; 
        font-weight: 700; 
        color: #0f172a !important; 
        margin-top: 14px; 
        line-height: 1.5;
    }
    
    .badge-category {
        background-color: #eff6ff !important; 
        color: #1d4ed8 !important;
        border: 1px solid #bfdbfe !important; 
        padding: 6px 16px; 
        border-radius: 30px; 
        font-weight: 700;
        font-size: 0.85rem;
    }
    .badge-difficulty {
        background-color: #f1f5f9 !important; 
        color: #334155 !important;
        border: 1px solid #cbd5e1 !important; 
        padding: 6px 16px; 
        border-radius: 30px; 
        font-weight: 700; 
        font-size: 0.85rem;
        margin-left: 8px;
    }

    .stTextArea textarea {
        background-color: #ffffff !important; 
        color: #0f172a !important;
        border: 1.5px solid #cbd5e1 !important; 
        border-radius: 14px !important; 
        padding: 16px !important;
        font-size: 1rem !important;
        transition: all 0.2s ease !important;
    }
    .stTextArea textarea:focus {
        border-color: #2563eb !important;
        box-shadow: 0 0 0 4px rgba(37, 99, 235, 0.1) !important;
    }

    .side-card {
        background: #ffffff !important; 
        border-radius: 20px;
        border: 1px solid #e2e8f0; 
        padding: 24px; 
        margin-bottom: 20px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.03);
    }
    .progress-percent { 
        font-size: 2.5rem; 
        font-weight: 800; 
        color: #2563eb !important; 
        letter-spacing: -1px;
    }

    div[data-testid="stMetric"] {
        background: #ffffff !important;
        padding: 16px;
        border-radius: 16px;
        border: 1px solid #e2e8f0;
        box-shadow: 0 2px 6px rgba(0,0,0,0.02);
    }
</style>
""", unsafe_allow_html=True)

# 🛠️ TÜRKÇE HARF DÖNÜŞTÜRÜCÜ
def turkish_lower(text: str) -> str:
    if not text:
        return ""
    rep = {'I': 'ı', 'İ': 'i', 'Ç': 'ç', 'Ş': 'ş', 'Ğ': 'ğ', 'Ü': 'ü', 'Ö': 'ö'}
    for search, replace in rep.items():
        text = text.replace(search, replace)
    return text.lower()

# 🛠️ SESİ TÜRKÇE METNE ÇEVİREN SERVER-SIDE MOTOR
def transcribe_audio(audio_bytes):
    recognizer = sr.Recognizer()
    try:
        audio_file = io.BytesIO(audio_bytes)
        with sr.AudioFile(audio_file) as source:
            audio_data = recognizer.record(source)
            text = recognizer.recognize_google(audio_data, language="tr-TR")
            return text
    except Exception:
        return ""

# 🛠️ ESNEK KELİME EŞLEŞTİRME
def is_flexible_match(keyword: str, clean_answer: str) -> bool:
    clean_kw = turkish_lower(str(keyword).strip())
    clean_kw = re.sub(r'[^\w\s]', '', clean_kw)
    
    if not clean_kw:
        return False

    if clean_kw in clean_answer:
        return True

    words_in_kw = clean_kw.split()
    if len(words_in_kw) > 1:
        matched_parts = 0
        for w in words_in_kw:
            if len(w) >= 3:
                stem = w[:4] if len(w) >= 4 else w
                if stem in clean_answer:
                    matched_parts += 1
        if matched_parts >= 1:
            return True
    else:
        single_w = words_in_kw[0]
        if len(single_w) >= 4:
            stem = single_w[:4]
            if stem in clean_answer:
                return True
        elif single_w in clean_answer:
            return True

    return False

# 🛠️ ESNEK SKORLAMA (0, 30, 60, 80, 100)
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
        if is_flexible_match(kw, clean_answer):
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
if "last_processed_audio" not in st.session_state:
    st.session_state.last_processed_audio = None

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
        st.session_state.last_processed_audio = None

# Sidebar
st.sidebar.markdown("""
<div style="padding: 10px 0 20px 0;">
    <h2 style="color: #ffffff; margin:0; font-size: 1.5rem; font-weight:800;">✈️ PilotInterviewPro</h2>
    <p style="color: #93c5fd; font-size: 0.85rem; margin-top:4px;">Practice. Improve. Fly.</p>
</div>
""", unsafe_allow_html=True)

st.sidebar.markdown("---")

kategoriler = ["Tüm Kategoriler"] + sorted(list(set(q["category"] for q in questions_data))) if questions_data else []

def on_kategori_change():
    yeni_kat = st.session_state.kat_select_box
    st.session_state.secilen_kategori = yeni_kat
    yeni_soru_getir(yeni_kat)

kat_index = kategoriler.index(st.session_state.secilen_kategori) if st.session_state.secilen_kategori in kategoriler else 0

secilen_kategori = st.sidebar.selectbox(
    "🎯 Mülakat Kategorisi",
    kategoriler,
    index=kat_index,
    key="kat_select_box",
    on_change=on_kategori_change
)

if st.session_state.mevcut_soru is None and questions_data:
    yeni_soru_getir(st.session_state.secilen_kategori)

# Hero Banner
st.markdown("""
<div class="hero-banner animated-element">
    <div class="hero-title">Pilot Mülakatına Hazırlanın</div>
    <div class="hero-subtitle">
        Gerçek mülakat simülasyonu ile kendinizi sınayın. 
        Teknik bilginizi sesle yanıtlayın, anında tam otomatik değerlendirilsin.
    </div>
</div>
""", unsafe_allow_html=True)

# Üst Metrikler
toplam_soru = len(questions_data)
tamamlanan = len(st.session_state.puanlar)
ort_skor = (sum(st.session_state.puanlar) / tamamlanan) if tamamlanan > 0 else 0

st1, st2, st3, st4 = st.columns(4)
st1.metric("Toplam Soru", f"{toplam_soru}+")
st2.metric("Kategori", f"{len(kategoriler)-1} Başlık")
st3.metric("Ortalama Skor", f"%{ort_skor:.0f}")
st4.metric("Seviye", "ATPL & CPL")

st.markdown("<br>", unsafe_allow_html=True)

# Ana Ekran
col_left, col_right = st.columns([2.5, 1])

with col_left:
    if st.session_state.mevcut_soru:
        soru = st.session_state.mevcut_soru
        input_key = f"answer_input_{soru.get('id')}"
        
        # Soru Kartı
        st.markdown(f"""
        <div class="main-card animated-element">
            <div>
                <span class="badge-category">{soru.get('category', 'Genel')}</span>
                <span class="badge-difficulty">{soru.get('difficulty', 'Orta')}</span>
            </div>
            <div class="question-title">❓ {soru.get('question', '')}</div>
        </div>
        """, unsafe_allow_html=True)
        
        with st.expander("💡 Mülakatçı Beklentileri (Kilit Terim İpuçları)"):
            st.write("Bu soruda yanıtınızda bulunması hedeflenen bazı kilit kavramlar:")
            kw_list = soru.get("keywords", [])
            if kw_list:
                for kp in kw_list[:2]:
                    st.write(f"- **{kp}**")
                st.write("*...ve diğer ilgili havacılık terimleri.*")

        st.write("### 🎙️ Sesli Yanıt Verin")
        st.caption("Mikrofona basıp konuşun. 5 saniye susursanız veya mikrofona tekrar basarsanız **sesiniz yazılı alana aktarılır ve otomatik puanlanır.**")

        # 🎙️ OTOMATİK TAM DEĞERLENDİRMELİ SES KAYDEDİCİ
        audio_bytes = audio_recorder(
            text="Mikrofona Bas ve Konuş",
            recording_color="#e11d48",
            neutral_color="#2563eb",
            icon_name="microphone",
            icon_size="2x",
            pause_threshold=5.0
        )

        # Ses Çözümleme ve State Güncelleme
        if audio_bytes and audio_bytes != st.session_state.last_processed_audio:
            st.session_state.last_processed_audio = audio_bytes
            with st.spinner("🔊 Sesiniz metne dönüştürülüyor..."):
                transcribed_text = transcribe_audio(audio_bytes)
                
                if transcribed_text.strip():
                    # Doğrudan text_area'nın bağlı olduğu state tuşunu güncelle
                    st.session_state[input_key] = transcribed_text
                    
                    keywords = soru.get("keywords", [])
                    eval_result = calculate_score(transcribed_text, keywords)
                    
                    puan = eval_result["score"]
                    st.session_state.puanlar.append(puan)
                    
                    st.session_state.son_analiz = {
                        "puan": puan,
                        "matched_count": eval_result["matched_count"],
                        "bulunanlar": eval_result["matched_keywords"],
                        "bulunamayanlar": eval_result["missing_keywords"],
                        "metin": transcribed_text
                    }
                    st.rerun()
                else:
                    st.warning("⚠️ Ses anlaşılamadı. Lütfen biraz daha net konuşarak tekrar deneyin.")

        # Algılanan veya Yazılan Yanıt Kutusu
        kullanici_cevabi = st.text_area(
            "Algılanan / Yazılan Yanıtınız:",
            placeholder="Sesli konuştuğunuzda metin buraya aktarılır veya buraya yazabilirsiniz...",
            height=120,
            key=input_key
        )

        btn_c1, btn_c2 = st.columns([1, 1])
        with btn_c1:
            if st.button("💾 Yanıtı Değerlendir", type="primary", use_container_width=True):
                if kullanici_cevabi.strip():
                    keywords = soru.get("keywords", [])
                    eval_result = calculate_score(kullanici_cevabi, keywords)
                    
                    puan = eval_result["score"]
                    st.session_state.puanlar.append(puan)
                    
                    st.session_state.son_analiz = {
                        "puan": puan,
                        "matched_count": eval_result["matched_count"],
                        "bulunanlar": eval_result["matched_keywords"],
                        "bulunamayanlar": eval_result["missing_keywords"],
                        "metin": kullanici_cevabi
                    }
                    st.rerun()
                else:
                    st.warning("⚠️ Lütfen değerlendirmek için bir metin yazın.")
        
        with btn_c2:
            if st.button("Sonraki Soruya Geç ➔", use_container_width=True):
                yeni_soru_getir(st.session_state.secilen_kategori)
                st.rerun()

        # Karnedeki Değerlendirme Çıktısı (Animasyonlu)
        if st.session_state.son_analiz:
            res = st.session_state.son_analiz
            puan = res["puan"]
            matched_cnt = res["matched_count"]
            
            st.markdown("---")
            st.markdown("<div class='animated-element'>", unsafe_allow_html=True)
            st.subheader("📋 Mülakat Değerlendirme Karnesi")
            
            if puan == 100:
                st.success(f"🏆 **Mülakat Skoru: 100 / 100** — Mükemmel! Konuya tam hakimsiniz ({matched_cnt} kilit kavram yakalandı).")
            elif puan == 80:
                st.info(f"🥇 **Mülakat Skoru: 80 / 100** — Çok İyi! Kilit terimler büyük oranda mevcut.")
            elif puan == 60:
                st.warning(f"⚠️ **Mülakat Skoru: 60 / 100** — Geçer/Orta Seviye. Bazı detayları unuttunuz.")
            elif puan == 30:
                st.error(f"🔴 **Mülakat Skoru: 30 / 100** — Zayıf. Temel terminolojiden uzak kalındı.")
            else:
                st.error(f"❌ **Mülakat Skoru: 0 / 100** — Yetersiz. Yanıtınızda anahtar kavramlar bulunamadı.")

            c_pos, c_neg = st.columns(2)
            with c_pos:
                st.write("##### ✅ Yakalanan Kilit Kavramlar")
                if res["bulunanlar"]:
                    for b in res["bulunanlar"]:
                        st.write(f"✔️ **{b}**")
                else:
                    st.info("Cevabınızda kilit kavramlar yakalanamadı.")

            with c_neg:
                st.write("##### ❌ Eksik/Atlanan Kavramlar")
                if res["bulunamayanlar"]:
                    for ex in res["bulunamayanlar"]:
                        st.write(f"✖️ {ex}")
                else:
                    st.success("Tüm kilit noktalar yanıtınızda mevcut!")
            st.markdown("</div>", unsafe_allow_html=True)

# SAĞ PANEL
with col_right:
    yuzde = int((tamamlanan / toplam_soru) * 100) if toplam_soru > 0 else 0
    
    st.markdown(f"""
    <div class="side-card animated-element">
        <h4 style="margin:0 0 10px 0; color:#0f172a; font-weight:700;">📊 Genel İlerleme</h4>
        <div class="progress-percent">%{yuzde}</div>
        <p style="margin:6px 0 0 0; color:#64748b; font-size:0.9rem;">
            Toplam <b>{toplam_soru}</b> sorudan <b>{tamamlanan}</b> tanesi yanıtlandı.
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    st.progress(min(yuzde / 100, 1.0))
