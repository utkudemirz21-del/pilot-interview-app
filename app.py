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

# Session State Başlatma
if "sorulan_ids" not in st.session_state:
    st.session_state.sorulan_ids = []
if "mevcut_soru" not in st.session_state:
    st.session_state.mevcut_soru = None
if "puanlar" not in st.session_state:
    st.session_state.puanlar = []
if "son_analiz" not in st.session_state:
    st.session_state.son_analiz = None

# Soru Değiştirme ve Filtreleme Fonksiyonu
def yeni_soru_getir(kategori_filtresi):
    if kategori_filtresi == "Tüm Kategoriler":
        filtre = questions_data
    else:
        filtre = [q for q in questions_data if q.get("category") == kategori_filtresi]
    
    if not filtre:
        st.session_state.mevcut_soru = None
        return

    kullanilabilir = [q for q in filtre if q["id"] not in st.session_state.sorulan_ids]
    
    # Tüm sorular sorulduysa geçmişi sıfırla
    if not kullanilabilir:
        st.session_state.sorulan_ids = [q_id for q_id in st.session_state.sorulan_ids if q_id not in [q["id"] for q in filtre]]
        kullanilabilir = filtre

    if kullanilabilir:
        secilen = random.choice(kullanilabilir)
        st.session_state.mevcut_soru = secilen
        st.session_state.sorulan_ids.append(secilen["id"])
        st.session_state.son_analiz = None

# SOL MENÜ (Sidebar)
st.sidebar.title("✈️ PilotInterviewPro")
st.sidebar.caption("Practice. Improve. Fly.")
st.sidebar.markdown("---")

kategoriler = ["Tüm Kategoriler"] + sorted(list(set(q["category"] for q in questions_data))) if questions_data else []

# Kategori Değiştiğinde Anında Yeni Soru Getir
def on_kategori_change():
    secilen = st.session_state.kat_secim_key
    yeni_soru_getir(secilen)

secilen_kategori = st.sidebar.selectbox(
    "🎯 Mülakat Kategorisi Seçin",
    kategoriler,
    key="kat_secim_key",
    on_change=on_kategori_change
)

# İlk Açılışta Soru Getir
if st.session_state.mevcut_soru is None and questions_data:
    yeni_soru_getir(secilen_kategori)

st.sidebar.markdown("---")
st.sidebar.subheader("📊 Genel İlerleme")
toplam_soru = len(questions_data)
tamamlanan = len(st.session_state.puanlar)
ort_skor = (sum(st.session_state.puanlar) / tamamlanan) if tamamlanan > 0 else 0

st.sidebar.progress(min(tamamlanan / toplam_soru, 1.0) if toplam_soru > 0 else 0.0)
st.sidebar.write(f"**Tamamlanan:** {tamamlanan} / {toplam_soru} Soru")
st.sidebar.write(f"**Ortalama Başarı:** %{ort_skor:.0f}")

# ANA SAYFA BAŞLIK & İSTATİSTİKLER
st.title("✈️ Pilot Mülakatına Hazırlanın")
st.write("Gerçek mülakat deneyimini simüle eden teknik sorularla kendinizi geliştirin.")

col1, col2, col3, col4 = st.columns(4)
col1.metric("Toplam Soru", f"{toplam_soru}+")
col2.metric("Kategori", f"{len(kategoriler)-1} Başlık")
col3.metric("Ortalama Skor", f"%{ort_skor:.0f}")
col4.metric("Seviye", "ATPL & CPL")

st.markdown("---")

# ANA İÇERİK ALANI
col_main, col_info = st.columns([2.5, 1])

with col_main:
    if st.session_state.mevcut_soru:
        soru = st.session_state.mevcut_soru
        
        # Soru Kartı
        st.subheader(f"📌 {soru['category']}  ·  ({soru['difficulty']})")
        st.info(f"### ❓ {soru['question']}")
        
        with st.expander("💡 Mülakatçı Beklentileri (Kilit Terimler)"):
            st.write("Cevabınızda değerlendirilecek temel noktalar:")
            for kp in soru.get("key_points", []):
                st.write(f"- **{kp}**")

        kullanici_cevabi = st.text_area(
            "Cevabınızı Yazılı Olarak Verin:",
            placeholder="Havacılık terminolojisine (ICAO/SOP) uygun şekilde detaylıca yanıtlayın...",
            height=150
        )

        c1, c2 = st.columns(2)
        with c1:
            cevapla_btn = st.button("🚀 Yanıtı Kaydet ve Değerlendir", type="primary", use_container_width=True)
        with c2:
            if st.button("Sonraki Soru ➔", use_container_width=True):
                yeni_soru_getir(secilen_kategori)
                st.rerun()

        # Otomatik Değerlendirme Motoru
        if cevapla_btn:
            if not kullanici_cevabi.strip():
                st.warning("⚠️ Lütfen önce bir cevap yazın.")
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

        # Değerlendirme Sonucu
        if st.session_state.son_analiz:
            res = st.session_state.son_analiz
            puan = res["puan"]
            
            st.markdown("---")
            st.subheader("📋 Mülakat Değerlendirme Karnesi")
            
            if puan >= 80:
                st.success(f"🏆 **Mülakat Skoru: {puan} / 100** — Harika! Konuya ve terminolojiye hakimsiniz.")
            elif puan >= 50:
                st.warning(f"⚠️ **Mülakat Skoru: {puan} / 100** — Geçer Seviye. Bazı kilit detaylar eksik kaldı.")
            else:
                st.error(f"❌ **Mülakat Skoru: {puan} / 100** — Yetersiz. Temel teknik terimleri tekrar gözden geçirmelisiniz.")

            col_pos, col_neg = st.columns(2)
            with col_pos:
                st.write("##### ✅ Tespit Edilen Doğru Noktalar")
                if res["bulunanlar"]:
                    for b in res["bulunanlar"]:
                        st.success(f"✔️ {b}")
                else:
                    st.info("Kilit kavramlar bulunamadı.")

            with col_neg:
                st.write("##### ❌ Eksik veya Atlanan Noktalar")
                if res["bulunamayanlar"]:
                    for ex in res["bulunamayanlar"]:
                        st.error(f"✖️ {ex}")
                else:
                    st.success("Tüm kilit noktalar mevcut!")

with col_info:
    st.write("### 💡 Mülakat İpucu")
    st.info(
        "Teknik sorularda sadece doğru cevabı vermek değil, mantığınızı açıklamak da çok önemlidir. "
        "Neden-sonuç ilişkisini kurmayı ve havacılık terminolojisini (ICAO) kullanmayı unutmayın."
    )
