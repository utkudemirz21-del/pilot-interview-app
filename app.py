import json
import random
import re
import streamlit as st

# Sayfa Yapılandırması
st.set_page_config(
    page_title="CockpitPrep - Pilot Teknik Mülakat Simülatörü",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Aydınlık / Mavi-Beyaz Odaklı Modern CSS Tasarımı
st.markdown("""
<style>
    /* Temel Arka Plan ve Yazı Tipi */
    .stApp {
        background-color: #f8fafc;
        color: #1e293b;
        font-family: 'Inter', system-ui, -apple-system, sans-serif;
    }
    
    /* Yan Menü (Sidebar) */
    section[data-testid="stSidebar"] {
        background-color: #ffffff;
        border-right: 1px solid #e2e8f0;
    }
    
    /* Header Alanı */
    .header-container {
        background: linear-gradient(90deg, #1e3a8a 0%, #2563eb 100%);
        padding: 24px 32px;
        border-radius: 16px;
        color: #ffffff;
        margin-bottom: 24px;
        box-shadow: 0 4px 20px rgba(37, 99, 235, 0.15);
    }
    .header-title {
        font-size: 1.8rem;
        font-weight: 700;
        margin: 0;
        color: #ffffff;
    }
    .header-subtitle {
        font-size: 0.95rem;
        color: #bfdbfe;
        margin-top: 4px;
    }

    /* Soru Kartı Tasarımı */
    .question-card {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 16px;
        padding: 28px;
        margin-bottom: 20px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03);
    }
    
    .question-text {
        color: #0f172a;
        font-size: 1.25rem;
        font-weight: 600;
        line-height: 1.6;
        margin-top: 12px;
    }

    /* Rozetler (Badges) */
    .badge-category {
        background-color: #eff6ff;
        color: #1d4ed8;
        border: 1px solid #bfdbfe;
        padding: 6px 14px;
        border-radius: 20px;
        font-size: 0.85rem;
        font-weight: 600;
        display: inline-block;
        margin-right: 8px;
    }
    
    .badge-difficulty {
        background-color: #f1f5f9;
        color: #475569;
        border: 1px solid #cbd5e1;
        padding: 6px 14px;
        border-radius: 20px;
        font-size: 0.85rem;
        font-weight: 500;
        display: inline-block;
    }

    /* Skor Kutuları */
    .score-card {
        background-color: #ffffff;
        border-radius: 16px;
        padding: 24px;
        border: 1px solid #e2e8f0;
        box-shadow: 0 4px 12px rgba(0,0,0,0.03);
        margin-bottom: 20px;
    }
    
    .score-high {
        border-left: 6px solid #10b981;
    }
    .score-medium {
        border-left: 6px solid #f59e0b;
    }
    .score-low {
        border-left: 6px solid #ef4444;
    }

    /* Metin Kutuları ve Alanlar */
    .stTextArea textarea {
        background-color: #ffffff !important;
        color: #0f172a !important;
        border: 1.5px solid #cbd5e1 !important;
        border-radius: 12px !important;
        font-size: 0.98rem !important;
        padding: 14px !important;
    }
    .stTextArea textarea:focus {
        border-color: #2563eb !important;
        box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1) !important;
    }

    /* Buton İyileştirmeleri */
    .stButton > button[data-baseweb="button"] {
        border-radius: 10px !important;
        font-weight: 600 !important;
    }
</style>
""", unsafe_allow_html=True)

# JSON Verisini Yükle
@st.cache_data
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

# Başlık Kartı
st.markdown("""
<div class="header-container">
    <div class="header-title">✈️ CockpitPrep — Pilot Mülakat Simülatörü</div>
    <div class="header-subtitle">ATPL & Havayolu Mülakatları İçin İnteraktif Teknik Değerlendirme Platformu</div>
</div>
""", unsafe_allow_html=True)

# Yan Menü (Sidebar)
st.sidebar.title("✈️ Kontrol Paneli")

kategoriler = ["Tüm Kategoriler"] + sorted(list(set(q["category"] for q in questions_data))) if questions_data else []
secilen_kategori = st.sidebar.selectbox("🎯 Mülakat Konusu", kategoriler, key="kat_secim")

def yeni_soru_getir():
    filtre = questions_data
    if secilen_kategori != "Tüm Kategoriler":
        filtre = [q for q in questions_data if q["category"] == secilen_kategori]
    
    kullanilabilir = [q for q in filtre if q["id"] not in st.session_state.sorulan_ids]
    
    if not kullanilabilir:
        st.session_state.sorulan_ids = []
        kullanilabilir = filtre

    if kullanilabilir:
        secilen = random.choice(kullanilabilir)
        st.session_state.mevcut_soru = secilen
        st.session_state.sorulan_ids.append(secilen["id"])
        st.session_state.son_analiz = None

if st.session_state.mevcut_soru is None and questions_data:
    yeni_soru_getir()

# Sidebar Performans Paneli
st.sidebar.markdown("---")
st.sidebar.subheader("📊 İlerleme ve Skor")
if st.session_state.puanlar:
    ort = sum(st.session_state.puanlar) / len(st.session_state.puanlar)
    st.sidebar.metric("Ortalama Başarı", f"%{ort:.0f}")
    st.sidebar.metric("Yanıtlanan Soru", len(st.session_state.puanlar))
    st.sidebar.progress(int(ort) / 100)
else:
    st.sidebar.info("Henüz yanıtlanan soru yok.")

# Ana İçerik
if st.session_state.mevcut_soru:
    soru = st.session_state.mevcut_soru
    
    # Şık Beyaz Soru Kartı
    st.markdown(f"""
    <div class="question-card">
        <div>
            <span class="badge-category">{soru['category']}</span>
            <span class="badge-difficulty">{soru['difficulty']}</span>
        </div>
        <div class="question-text">❓ {soru['question']}</div>
    </div>
    """, unsafe_allow_html=True)
    
    with st.expander("💡 Mülakatçı Beklentileri (Kilit Terimler)"):
        st.write("Bu soruda yanıtınızda geçmesi beklenen anahtar kavramlar:")
        for kp in soru.get("key_points", []):
            st.markdown(f"- **{kp}**")

    kullanici_cevabi = st.text_area(
        "Mülakat Yanıtınız:",
        placeholder="Havacılık terminolojisine (ICAO/SOP) uygun şekilde yanıtınızı detaylıca açıklayın...",
        height=150
    )

    c_btn1, c_btn2, _ = st.columns([2, 2, 4])
    with c_btn1:
        cevapla_btn = st.button("🚀 Yanıtı Gönder ve Değerlendir", type="primary", use_container_width=True)
    with c_btn2:
        if st.button("Sonraki Soruya Geç ➔", use_container_width=True):
            yeni_soru_getir()
            st.rerun()

    # Otomatik Değerlendirme Motoru
    if cevapla_btn:
        if not kullanici_cevabi.strip():
            st.warning("⚠️ Lütfen önce mülakat yanıtınızı metin alanına yazın.")
        else:
            key_points = soru.get("key_points", [])
            cevabi_alt = kullanici_cevabi.lower()
            
            bulunanlar = []
            bulunamayanlar = []

            for kp in key_points:
                terimler = re.findall(r'\b\w{3,}\b', kp.lower())
                bulundu = any(t in cevabi_alt for t in terimler)
                
                if bulundu:
                    bulunanlar.append(kp)
                else:
                    bulunamayanlar.append(kp)

            toplam_kriter = len(key_points)
            puan = int((len(bulunanlar) / toplam_kriter) * 100) if toplam_kriter > 0 else 100

            st.session_state.puanlar.append(puan)
            st.session_state.son_analiz = {
                "puan": puan,
                "bulunanlar": bulunanlar,
                "bulunamayanlar": bulunamayanlar
            }

    # Değerlendirme Karnesi
    if st.session_state.son_analiz:
        res = st.session_state.son_analiz
        puan = res["puan"]
        
        st.markdown("<br>", unsafe_allow_html=True)
        st.subheader("📋 Mülakat Değerlendirme Karnesi")
        
        # Dinamik Beyaz Skor Kartı
        score_class = "score-high" if puan >= 80 else ("score-medium" if puan >= 50 else "score-low")
        status_text = "Mükemmel! Konuya ve terminolojiye hakimsiniz." if puan >= 80 else ("Geçer Seviye. Bazı kilit detaylar eksik kaldı." if puan >= 50 else "Yetersiz. Teknik terimleri ve detayları gözden geçirmelisiniz.")
        
        st.markdown(f"""
        <div class="score-card {score_class}">
            <h2 style="margin:0; color:#0f172a;">Skor: {puan} / 100</h2>
            <p style="margin:6px 0 0 0; color:#475569; font-size:1rem;">{status_text}</p>
        </div>
        """, unsafe_allow_html=True)

        col_pos, col_neg = st.columns(2)
        
        with col_pos:
            st.markdown("##### ✅ Yanıtınızda Tespit Edilen Doğru Noktalar")
            if res["bulunanlar"]:
                for b in res["bulunanlar"]:
                    st.success(f"✔️ {b}")
            else:
                st.info("Yanıtınızda beklenen kilit kavramlar tespit edilemedi.")

        with col_neg:
            st.markdown("##### ❌ Eksik veya Atlanan Kritik Noktalar")
            if res["bulunamayanlar"]:
                for ex in res["bulunamayanlar"]:
                    st.error(f"✖️ {ex}")
            else:
                st.success("Tebrikler, tüm anahtar noktaları cevabınızda kapsadınız!")
            
