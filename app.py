import json
import random
import re
import streamlit as st

# Sayfa Yapılandırması
st.set_page_config(
    page_title="PilotInterviewPro - Mülakat Hazırlık Platformu",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Görseldeki Profesyonel Tasarıma (PilotInterviewPro) Birebir Uygun CSS
st.markdown("""
<style>
    /* Global Temizlik ve Font */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    html, body, [class*="st-"] {
        font-family: 'Inter', sans-serif !important;
    }
    
    .stApp {
        background-color: #f4f6f9 !important;
        color: #1e293b !important;
    }

    /* Sol Menü - Derin Lacivert (Sidebar) */
    section[data-testid="stSidebar"] {
        background-color: #0b2559 !important;
        color: #ffffff !important;
        border: none !important;
    }
    section[data-testid="stSidebar"] * {
        color: #ffffff !important;
    }
    
    /* Hero Banner (Üst Görsel Alanı) */
    .hero-banner {
        position: relative;
        background: linear-gradient(135deg, rgba(11, 37, 89, 0.85) 0%, rgba(29, 78, 216, 0.7) 100%), 
                    url('https://images.unsplash.com/photo-1540959733332-eab4deabeeaf?q=80&w=1200&auto=format&fit=crop');
        background-size: cover;
        background-position: center;
        border-radius: 16px;
        padding: 36px 40px;
        color: #ffffff;
        margin-bottom: 24px;
        box-shadow: 0 10px 25px -5px rgba(11, 37, 89, 0.15);
    }
    .hero-title {
        font-size: 2.2rem;
        font-weight: 700;
        margin-bottom: 8px;
        color: #ffffff !important;
    }
    .hero-subtitle {
        font-size: 1.05rem;
        color: #e2e8f0 !important;
        max-width: 650px;
        line-height: 1.5;
    }

    /* İstatistik Mini Kartları */
    .stat-card {
        background: #ffffff;
        border-radius: 12px;
        padding: 16px 20px;
        border: 1px solid #e2e8f0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.02);
        display: flex;
        align-items: center;
        gap: 16px;
    }
    .stat-icon {
        font-size: 1.8rem;
        color: #2563eb;
    }
    .stat-label {
        font-size: 0.85rem;
        color: #64748b;
        font-weight: 500;
    }
    .stat-value {
        font-size: 1.15rem;
        font-weight: 700;
        color: #0f172a;
    }

    /* Soru ve Çalışma Kartı */
    .main-card {
        background: #ffffff;
        border-radius: 16px;
        border: 1px solid #e2e8f0;
        padding: 28px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.03);
        margin-bottom: 20px;
    }
    .question-title {
        font-size: 1.35rem;
        font-weight: 700;
        color: #0f172a;
        margin: 16px 0;
        line-height: 1.5;
    }
    
    /* Rozetler */
    .badge-blue {
        background-color: #eff6ff;
        color: #2563eb;
        border: 1px solid #bfdbfe;
        padding: 6px 14px;
        border-radius: 20px;
        font-size: 0.85rem;
        font-weight: 600;
    }

    /* Input & Textarea Özelleştirme */
    .stTextArea textarea {
        background-color: #f8fafc !important;
        color: #0f172a !important;
        border: 1.5px solid #cbd5e1 !important;
        border-radius: 12px !important;
        padding: 16px !important;
        font-size: 1rem !important;
    }
    .stTextArea textarea:focus {
        border-color: #2563eb !important;
        background-color: #ffffff !important;
    }

    /* Mavi Butonlar */
    .stButton > button[data-baseweb="button"] {
        border-radius: 10px !important;
        font-weight: 600 !important;
        padding: 10px 20px !important;
    }

    /* Sağ Panel Kartları */
    .side-card {
        background: #ffffff;
        border-radius: 16px;
        border: 1px solid #e2e8f0;
        padding: 20px;
        margin-bottom: 16px;
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

# Sol Menü (Sidebar) Logo & Navigasyon
st.sidebar.markdown("""
<div style="padding: 10px 0 20px 0; text-align: left;">
    <h2 style="color: #ffffff; margin:0; font-size: 1.5rem;">✈️ PilotInterviewPro</h2>
    <p style="color: #93c5fd; font-size: 0.8rem; margin-top:2px;">Practice. Improve. Fly.</p>
</div>
""", unsafe_allow_html=True)

st.sidebar.markdown("---")
kategoriler = ["Tüm Kategoriler"] + sorted(list(set(q["category"] for q in questions_data))) if questions_data else []
secilen_kategori = st.sidebar.selectbox("🎯 Mülakat Kategorisi", kategoriler, key="kat_secim")

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

# Hero Banner
st.markdown("""
<div class="hero-banner">
    <div class="hero-title">Pilot Mülakatına Hazırlanın</div>
    <div class="hero-subtitle">
        Gerçek mülakat deneyimini simüle eden sorularla kendinizi geliştirin. 
        Teknik bilginizi, CRM becerilerinizi ve iletişim yeteneklerinizi test edin.
    </div>
</div>
""", unsafe_allow_html=True)

# 4'lü Üst İstatistik Barı
st1, st2, st3, st4 = st.columns(4)
with st1:
    st.markdown(f"""
    <div class="stat-card">
        <div class="stat-icon">🎯</div>
        <div>
            <div class="stat-label">Toplam Soru</div>
            <div class="stat-value">{len(questions_data)}+</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

with st2:
    st.markdown(f"""
    <div class="stat-card">
        <div class="stat-icon">📊</div>
        <div>
            <div class="stat-label">Kategori</div>
            <div class="stat-value">{len(kategoriler)-1} Ana Başlık</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

with st3:
    ort = (sum(st.session_state.puanlar) / len(st.session_state.puanlar)) if st.session_state.puanlar else 0
    st.markdown(f"""
    <div class="stat-card">
        <div class="stat-icon">📈</div>
        <div>
            <div class="stat-label">Ortalama Skor</div>
            <div class="stat-value">%{ort:.0f}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

with st4:
    st.markdown(f"""
    <div class="stat-card">
        <div class="stat-icon">⭐</div>
        <div>
            <div class="stat-label">Seviye</div>
            <div class="stat-value">ATPL & CPL</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# Ana Düzen: Sol (Mülakat Alanı) & Sağ (Açıklama/İlerleme Paneli)
col_left, col_right = st.columns([2.2, 1])

with col_left:
    if st.session_state.mevcut_soru:
        soru = st.session_state.mevcut_soru
        
        # Soru Kartı
        st.markdown(f"""
        <div class="main-card">
            <div>
                <span class="badge-blue">{soru['category']}</span>
                <span style="color:#64748b; font-size:0.85rem; margin-left:8px;">{soru['difficulty']}</span>
            </div>
            <div class="question-title">❓ {soru['question']}</div>
        </div>
        """, unsafe_allow_html=True)
        
        with st.expander("💡 Mülakatçı Beklentileri (Kilit Terimler)"):
            st.write("Bu soruda yanıtınızda geçmesi beklenen anahtar kavramlar:")
            for kp in soru.get("key_points", []):
                st.markdown(f"- **{kp}**")

        kullanici_cevabi = st.text_area(
            "Cevabınızı Yazılı Olarak Verin:",
            placeholder="Havacılık terminolojisine (ICAO/SOP) uygun şekilde yanıtınızı detaylıca açıklayın...",
            height=160
        )

        btn_c1, btn_c2 = st.columns([1, 1])
        with btn_c1:
            cevapla_btn = st.button("💾 Yanıtı Kaydet ve Değerlendir", type="primary", use_container_width=True)
        with btn_c2:
            if st.button("Sonraki Soru ➔", use_container_width=True):
                yeni_soru_getir()
                st.rerun()

        # Değerlendirme Motoru
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
            st.subheader("📋 Mülakat Değerlendirme Karnesi")
            
            if puan >= 80:
                st.success(f"🏆 **Mülakat Skoru: {puan} / 100** — Harika! Konuya ve terminolojiye tam hakimsiniz.")
            elif puan >= 50:
                st.warning(f"⚠️ **Mülakat Skoru: {puan} / 100** — Geçer Seviye. Bazı kilit detayları unuttunuz.")
            else:
                st.error(f"❌ **Mülakat Skoru: {puan} / 100** — Yetersiz. Temel teknik terimleri tekrar gözden geçirmelisiniz.")

            c_pos, c_neg = st.columns(2)
            with c_pos:
                st.markdown("##### ✅ Tespit Edilen Doğru Noktalar")
                if res["bulunanlar"]:
                    for b in res["bulunanlar"]:
                        st.write(f"✔️ {b}")
                else:
                    st.info("Kilit kavramlar bulunamadı.")

            with c_neg:
                st.markdown("##### ❌ Eksik veya Atlanan Noktalar")
                if res["bulunamayanlar"]:
                    for ex in res["bulunamayanlar"]:
                        st.write(f"✖️ {ex}")
                else:
                    st.success("Tüm kilit noktalar mevcut!")

with col_right:
    # Sağ Taraf: Genel İlerleme & İpucu Kutusu (Görseldeki gibi)
    st.markdown("""
    <div class="side-card">
        <h4 style="margin:0 0 12px 0; color:#0f172a;">📊 Genel İlerleme</h4>
    </div>
    """, unsafe_allow_html=True)
    
    toplam_cevap = len(st.session_state.puanlar)
    yuzde = int((toplam_cevap / len(questions_data)) * 100) if questions_data else 0
    st.progress(min(yuzde / 100, 1.0))
    st.caption(f"Toplam {len(questions_data)} sorudan {toplam_cevap} tanesini tamamladınız (%{yuzde}).")

    st.markdown("<br>", unsafe_allow_html=True)
    
    st.markdown("""
    <div class="side-card" style="background:#eff6ff; border-color:#bfdbfe;">
        <h5 style="margin:0 0 8px 0; color:#1d4ed8;">💡 Küçük Bir İpucu</h5>
        <p style="margin:0; color:#1e40af; font-size:0.9rem; line-height:1.5;">
            Teknik sorularda sadece doğru cevabı vermek değil, mantığınızı açıklamak da çok önemlidir. 
            Neden-sonuç ilişkisini kurmayı unutmayın.
        </p>
    </div>
    """, unsafe_allow_html=True)
