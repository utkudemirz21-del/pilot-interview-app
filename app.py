import json
import random
import re
import streamlit as st

# Sayfa Yapılandırması
st.set_page_config(
    page_title="PilotInterviewPro",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Kesin Görünürlük ve Kontrast CSS'i
st.markdown("""
<style>
    /* Ana Arka Plan */
    .stApp {
        background-color: #f8fafc !important;
        color: #0f172a !important;
    }

    /* Sol Menü (Sidebar) - Derin Lacivert */
    section[data-testid="stSidebar"] {
        background-color: #0b2559 !important;
    }
    section[data-testid="stSidebar"] label {
        color: #ffffff !important;
        font-weight: 700 !important;
        font-size: 0.95rem !important;
    }

    /* SELECTBOX KUTUSU VE SEÇİLİ YAZI RENK DÜZELTMESİ */
    div[data-baseweb="select"] {
        background-color: #ffffff !important;
        border-radius: 8px !important;
    }
    div[data-baseweb="select"] * {
        color: #0f172a !important;
        fill: #0f172a !important;
        font-weight: 700 !important;
    }
    div[data-baseweb="select"] > div {
        background-color: #ffffff !important;
        border: 2px solid #cbd5e1 !important;
        border-radius: 8px !important;
    }
    
    /* Açılır Menü Seçenek Listesi */
    ul[role="listbox"] {
        background-color: #ffffff !important;
        border: 1px solid #cbd5e1 !important;
    }
    ul[role="listbox"] li {
        color: #0f172a !important;
        background-color: #ffffff !important;
        font-weight: 600 !important;
    }
    ul[role="listbox"] li:hover {
        background-color: #eff6ff !important;
        color: #2563eb !important;
    }

    /* Hero Banner */
    .hero-banner {
        background: linear-gradient(135deg, rgba(11, 37, 89, 0.95) 0%, rgba(29, 78, 216, 0.85) 100%), 
                    url('https://images.unsplash.com/photo-1540959733332-eab4deabeeaf?q=80&w=1200&auto=format&fit=crop');
        background-size: cover;
        background-position: center;
        border-radius: 16px;
        padding: 32px;
        color: #ffffff !important;
        margin-bottom: 24px;
        box-shadow: 0 8px 20px rgba(11, 37, 89, 0.12);
    }
    .hero-title {
        font-size: 2rem;
        font-weight: 700;
        margin-bottom: 6px;
        color: #ffffff !important;
    }
    .hero-subtitle {
        font-size: 1rem;
        color: #e2e8f0 !important;
        max-width: 600px;
        line-height: 1.5;
    }

    /* Soru Kartı */
    .main-card {
        background: #ffffff !important;
        border-radius: 16px;
        border: 1px solid #e2e8f0;
        padding: 24px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.04);
        margin-bottom: 16px;
    }
    .question-title {
        font-size: 1.25rem;
        font-weight: 700;
        color: #0f172a !important;
        margin-top: 12px;
        line-height: 1.5;
    }
    
    /* Kategori Rozetleri */
    .badge-category {
        background-color: #dbeafe !important;
        color: #1e40af !important;
        border: 1.5px solid #93c5fd !important;
        padding: 6px 14px;
        border-radius: 20px;
        font-size: 0.9rem;
        font-weight: 800 !important;
        display: inline-block;
    }
    .badge-difficulty {
        background-color: #e2e8f0 !important;
        color: #1e293b !important;
        border: 1.5px solid #cbd5e1 !important;
        padding: 6px 14px;
        border-radius: 20px;
        font-size: 0.9rem;
        font-weight: 800 !important;
        display: inline-block;
        margin-left: 8px;
    }

    /* Text Area */
    .stTextArea textarea {
        background-color: #ffffff !important;
        color: #0f172a !important;
        border: 1.5px solid #cbd5e1 !important;
        border-radius: 12px !important;
        padding: 14px !important;
        font-size: 1rem !important;
    }
    .stTextArea textarea:focus {
        border-color: #2563eb !important;
    }

    /* Expander */
    .stExpander {
        background-color: #ffffff !important;
        border: 1px solid #e2e8f0 !important;
        border-radius: 12px !important;
    }
    .stExpander * {
        color: #0f172a !important;
    }

    /* Sağ Panel Kartları */
    .side-card {
        background: #ffffff !important;
        border-radius: 16px;
        border: 1px solid #e2e8f0;
        padding: 20px;
        margin-bottom: 16px;
    }
    .progress-percent {
        font-size: 2.2rem;
        font-weight: 800;
        color: #2563eb !important;
        margin-bottom: 4px;
    }
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
    clean_answer = re.sub(r'[^\w\s]', ' ', clean_answer)  # Noktalama işaretlerini boşluğa çevir

    matched_keywords = []
    missing_keywords = []

    for kw in keywords:
        clean_kw = turkish_lower(str(kw).strip())
        if clean_kw and clean_kw in clean_answer:
            matched_keywords.append(kw)
        else:
            missing_keywords.append(kw)

    match_count = len(matched_keywords)

    # 🎯 ÖZEL SKORLAMA KURALI
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

# Session State Yönetimi
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

# Soru Seçim Motoru
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
    <p style="color: #93c5fd; font-size: 0.8rem; margin-top:2px;">Practice. Improve. Fly.</p>
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
<div class="hero-banner">
    <div class="hero-title">Pilot Mülakatına Hazırlanın</div>
    <div class="hero-subtitle">
        Gerçek mülakat deneyimini simüle eden sorularla kendinizi geliştirin. 
        Teknik bilginizi ve havacılık terminolojinizi test edin.
    </div>
</div>
""", unsafe_allow_html=True)

# Üst Metrik Kartları
toplam_soru = len(questions_data)
tamamlanan = len(st.session_state.puanlar)
ort_skor = (sum(st.session_state.puanlar) / tamamlanan) if tamamlanan > 0 else 0

st1, st2, st3, st4 = st.columns(4)
st1.metric("Toplam Soru", f"{toplam_soru}+")
st2.metric("Kategori", f"{len(kategoriler)-1} Başlık")
st3.metric("Ortalama Skor", f"%{ort_skor:.0f}")
st4.metric("Seviye", "ATPL & CPL")

st.markdown("<br>", unsafe_allow_html=True)

# Ana İçerik Alanı
col_left, col_right = st.columns([2.3, 1])

with col_left:
    if st.session_state.mevcut_soru:
        soru = st.session_state.mevcut_soru
        
        # Soru Kartı
        st.markdown(f"""
        <div class="main-card">
            <div>
                <span class="badge-category">{soru.get('category', 'Genel')}</span>
                <span class="badge-difficulty">{soru.get('difficulty', 'Orta')}</span>
            </div>
            <div class="question-title">❓ {soru.get('question', '')}</div>
        </div>
        """, unsafe_allow_html=True)
        
        # İP UCU VE AÇIKLAMA ALANI
        with st.expander("💡 Mülakatçı Beklentileri (Kilit Terim İpuçları)"):
            st.write("Bu soruda yanıtınızda bulunması hedeflenen bazı kilit kavramlar:")
            kw_list = soru.get("keywords", [])
            if kw_list:
                for kp in kw_list[:2]:  # İlk 2 tanesini ipucu olarak göster
                    st.write(f"- **{kp}**")
                st.write("*...ve diğer ilgili havacılık terimleri.*")
            else:
                st.write("Bu soru için özel kilit terim tanımlanmamış.")

        kullanici_cevabi = st.text_area(
            "Cevabınızı Yazılı Olarak Verin:",
            placeholder="Havacılık terminolojisine (ICAO/SOP) uygun şekilde yanıtınızı detaylıca açıklayın...",
            height=150,
            key=f"input_{soru.get('id')}"
        )

        btn_c1, btn_c2 = st.columns([1, 1])
        with btn_c1:
            cevapla_btn = st.button("💾 Yanıtı Kaydet ve Değerlendir", type="primary", use_container_width=True)
        with btn_c2:
            if st.button("Sonraki Soru ➔", use_container_width=True):
                yeni_soru_getir(st.session_state.secilen_kategori)
                st.rerun()

        # Otomatik Değerlendirme Motoru
        if cevapla_btn:
            if not kullanici_cevabi.strip():
                st.warning("⚠️ Lütfen önce mülakat yanıtınızı metin alanına yazın.")
            else:
                keywords = soru.get("keywords", [])
                eval_result = calculate_score(kullanici_cevabi, keywords)
                
                puan = eval_result["score"]
                st.session_state.puanlar.append(puan)
                
                st.session_state.son_analiz = {
                    "puan": puan,
                    "matched_count": eval_result["matched_count"],
                    "bulunanlar": eval_result["matched_keywords"],
                    "bulunamayanlar": eval_result["missing_keywords"]
                }

        # Değerlendirme Karnesi Çıktısı
        if st.session_state.son_analiz:
            res = st.session_state.son_analiz
            puan = res["puan"]
            matched_cnt = res["matched_count"]
            
            st.markdown("---")
            st.subheader("📋 Mülakat Değerlendirme Karnesi")
            
            if puan == 100:
                st.success(f"🏆 **Mülakat Skoru: 100 / 100** — Mükemmel! En az 4 kilit terim tespit edildi ({matched_cnt} adet).")
            elif puan == 80:
                st.info(f"🥇 **Mülakat Skoru: 80 / 100** — Çok İyi! Tam 3 kilit terim yakalandı.")
            elif puan == 60:
                st.warning(f"⚠️ **Mülakat Skoru: 60 / 100** — Geçer/Orta Seviye. 2 kilit terim bulundu.")
            elif puan == 30:
                st.error(f"🔴 **Mülakat Skoru: 30 / 100** — Zayıf. Sadece 1 kilit terim yakalandı.")
            else:
                st.error(f"❌ **Mülakat Skoru: 0 / 100** — Yetersiz. Yanıtınızda hiçbir anahtar kelime bulunamadı.")

            c_pos, c_neg = st.columns(2)
            with c_pos:
                st.write("##### ✅ Tespit Edilen Doğru Noktalar")
                if res["bulunanlar"]:
                    for b in res["bulunanlar"]:
                        st.write(f"✔️ **{b}**")
                else:
                    st.info("Cevabınızda kilit kavramlar yakalanamadı.")

            with c_neg:
                st.write("##### ❌ Eksik veya Atlanan Noktalar")
                if res["bulunamayanlar"]:
                    for ex in res["bulunamayanlar"]:
                        st.write(f"✖️ {ex}")
                else:
                    st.success("Tüm kilit noktalar yanıtınızda mevcut!")

with col_right:
    # Sağ Taraf: Genel İlerleme (% Göstergeli) & İpucu Kutusu
    yuzde = int((tamamlanan / toplam_soru) * 100) if toplam_soru > 0 else 0
    
    st.markdown(f"""
    <div class="side-card">
        <h4 style="margin:0 0 8px 0; color:#0f172a;">📊 Genel İlerleme</h4>
        <div class="progress-percent">%{yuzde}</div>
        <p style="margin:0; color:#64748b; font-size:0.88rem;">
            Toplam <b>{toplam_soru}</b> sorudan <b>{tamamlanan}</b> tanesi yanıtlandı.
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    st.progress(min(yuzde / 100, 1.0))

    st.markdown("<br>", unsafe_allow_html=True)
    
    st.markdown("""
    <div class="side-card" style="background:#eff6ff !important; border-color:#bfdbfe !important;">
        <h5 style="margin:0 0 8px 0; color:#1d4ed8 !important;">💡 Değerlendirme Kriteri</h5>
        <p style="margin:0; color:#1e40af !important; font-size:0.88rem; line-height:1.5;">
            <b>Skor Tablosu:</b><br>
            • 4+ Keyword: <b>100 Puan</b><br>
            • 3 Keyword: <b>80 Puan</b><br>
            • 2 Keyword: <b>60 Puan</b><br>
            • 1 Keyword: <b>30 Puan</b><br>
            • 0 Keyword: <b>0 Puan</b>
        </p>
    </div>
    """, unsafe_allow_html=True)
