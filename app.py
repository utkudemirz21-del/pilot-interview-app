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

# Özel CSS İle Şık ve Modern Arayüz Tasarımı
st.markdown("""
<style>
    /* Ana Arka Plan ve Yazı Tipleri */
    .stApp {
        background-color: #0d1117;
        color: #c9d1d9;
    }
    
    /* Yan Menü (Sidebar) Şekillendirme */
    section[data-testid="stSidebar"] {
        background-color: #161b22;
        border-right: 1px solid #30363d;
    }
    
    /* Soru Kartı Tasarımı */
    .question-card {
        background: linear-gradient(135deg, #1f2937 0%, #111827 100%);
        border: 1px solid #374151;
        border-radius: 12px;
        padding: 24px;
        margin-bottom: 20px;
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.3);
    }
    
    .question-title {
        color: #60a5fa;
        font-size: 1.35rem;
        font-weight: 600;
        margin-bottom: 12px;
    }
    
    /* Rozetler (Badges) */
    .badge-category {
        background-color: #1e3a8a;
        color: #93c5fd;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.85rem;
        font-weight: 600;
        display: inline-block;
        margin-right: 8px;
    }
    
    .badge-difficulty {
        background-color: #374151;
        color: #e5e7eb;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.85rem;
        font-weight: 500;
        display: inline-block;
    }

    /* Puan Kartları */
    .score-box-high {
        background-color: rgba(16, 185, 129, 0.1);
        border: 1px solid #10b981;
        border-radius: 10px;
        padding: 16px;
        text-align: center;
        color: #34d399;
    }
    
    .score-box-medium {
        background-color: rgba(245, 158, 11, 0.1);
        border: 1px solid #f59e0b;
        border-radius: 10px;
        padding: 16px;
        text-align: center;
        color: #fbbf24;
    }
    
    .score-box-low {
        background-color: rgba(239, 68, 68, 0.1);
        border: 1px solid #ef4444;
        border-radius: 10px;
        padding: 16px;
        text-align: center;
        color: #f87171;
    }

    /* Metin Alanı Özelleştirme */
    .stTextArea textarea {
        background-color: #161b22 !important;
        color: #f3f4f6 !important;
        border: 1px solid #30363d !important;
        border-radius: 8px !important;
    }
    .stTextArea textarea:focus {
        border-color: #3b82f6 !important;
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

# Başlık Paneli
col_header, col_logo = st.columns([4, 1])
with col_header:
    st.title("✈️ CockpitPrep Simülatörü")
    st.caption("ATPL & Havayolu Mülakatları İçin İnteraktif Teknik Değerlendirme Platformu")

st.markdown("---")

# Yan Menü
st.sidebar.image("https://img.icons8.com/color/96/airplane-take-off.png", width=64)
st.sidebar.title("Kontrol Paneli")

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

# Sidebar Performans Göstergesi
st.sidebar.markdown("---")
st.sidebar.subheader("📊 Oturum Performansı")
if st.session_state.puanlar:
    ort = sum(st.session_state.puanlar) / len(st.session_state.puanlar)
    st.sidebar.metric("Ortalama Skor", f"{ort:.0f} / 100")
    st.sidebar.metric("Cevaplanan Soru", len(st.session_state.puanlar))
    st.sidebar.progress(int(ort) / 100)
else:
    st.sidebar.info("Henüz soru yanıtlanmadı.")

# Ana İçerik
if st.session_state.mevcut_soru:
    soru = st.session_state.mevcut_soru
    
    # Soru Kartı
    st.markdown(f"""
    <div class="question-card">
        <div style="margin-bottom: 12px;">
            <span class="badge-category">{soru['category']}</span>
            <span class="badge-difficulty">{soru['difficulty']}</span>
        </div>
        <div class="question-title">❓ {soru['question']}</div>
    </div>
    """, unsafe_allow_html=True)
    
    with st.expander("💡 Değerlendirme Kriterleri (Mülakatçı İpucu)"):
        st.write("Mülakat heyetinin cevapta aradığı temel kilit kavramlar:")
        for kp in soru.get("key_points", []):
            st.markdown(f"- **{kp}**")

    kullanici_cevabi = st.text_area(
        "Mülakat Yanıtınız:",
        placeholder="Havacılık terminolojisine (ICAO/SOP) uygun şekilde yanıtınızı detaylıca açıklayın...",
        height=160
    )

    c_btn1, c_btn2, _ = st.columns([2, 2, 4])
    with c_btn1:
        cevapla_btn = st.button("🚀 Cevabı Değerlendir", type="primary", use_container_width=True)
    with c_btn2:
        if st.button("Sonraki Soru ➔", use_container_width=True):
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

    # Değerlendirme Karnesi Çıktısı
    if st.session_state.son_analiz:
        res = st.session_state.son_analiz
        puan = res["puan"]
        
        st.markdown("<br>", unsafe_allow_html=True)
        st.subheader("📋 Mülakatçı Değerlendirme Karnesi")
        
        # Dinamik Skor Paneli
        if puan >= 80:
            st.markdown(f"""
            <div class="score-box-high">
                <h2 style="margin:0;">🏆 Mülakat Skoru: {puan} / 100</h2>
                <p style="margin:4px 0 0 0;">Mükemmel! Konuya ve havacılık terminolojisine son derece hakimsiniz.</p>
            </div>
            """, unsafe_allow_html=True)
        elif puan >= 50:
            st.markdown(f"""
            <div class="score-box-medium">
                <h2 style="margin:0;">⚠️ Mülakat Skoru: {puan} / 100</h2>
                <p style="margin:4px 0 0 0;">Geçer Seviye. Bazı kilit kavramlar veya detaylar eksik kaldı.</p>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class="score-box-low">
                <h2 style="margin:0;">❌ Mülakat Skoru: {puan} / 100</h2>
                <p style="margin:4px 0 0 0;">Yetersiz. Temel teknik terimleri ve prosedürleri tekrar gözden geçirmelisiniz.</p>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        col_pos, col_neg = st.columns(2)
        
        with col_pos:
            st.markdown("#### ✅ Yanıtınızda Yakalanan Doğru Noktalar")
            if res["bulunanlar"]:
                for b in res["bulunanlar"]:
                    st.success(f"✔️ {b}")
            else:
                st.info("Yanıtınızda beklenen kilit kavramlar tespit edilemedi.")

        with col_neg:
            st.markdown("#### ❌ Eksik veya Atlanan Kritik Noktalar")
            if res["bulunamayanlar"]:
                for ex in res["bulunamayanlar"]:
                    st.error(f"✖️ {ex}")
            else:
                st.success("Tebrikler, tüm anahtar noktaları cevabınızda eksiksiz kapsadınız!")
