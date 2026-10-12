import json
import random
import re
import streamlit as st

st.set_page_config(page_title="Pilot Teknik Mülakat Simülasyonu", page_icon="✈️", layout="wide")

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

# Session State Başlatma
if "sorulan_ids" not in st.session_state:
    st.session_state.sorulan_ids = []
if "mevcut_soru" not in st.session_state:
    st.session_state.mevcut_soru = None
if "puanlar" not in st.session_state:
    st.session_state.puanlar = []
if "son_analiz" not in st.session_state:
    st.session_state.son_analiz = None

st.title("✈️ Pilot Teknik Mülakat Simülasyonu")
st.write("Teknik havacılık bilginizi test edin. Cevabınız **100 üzerinden** otomatik değerlendirilir.")

# Yan Menü (Sidebar)
st.sidebar.header("🎯 Mülakat Konusu")
kategoriler = ["Tüm Kategoriler"] + sorted(list(set(q["category"] for q in questions_data))) if questions_data else []
secilen_kategori = st.sidebar.selectbox("Kategori Seçin:", kategoriler, key="kat_secim_sb")

# Soru Getirme Fonksiyonu
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

# Soru Yoksa İlk Soruyu Getir
if st.session_state.mevcut_soru is None and questions_data:
    yeni_soru_getir()

# İstatistikler
if st.session_state.puanlar:
    ort = sum(st.session_state.puanlar) / len(st.session_state.puanlar)
    st.sidebar.markdown("---")
    st.sidebar.metric("Ortalama Puan", f"{ort:.0f} / 100")
    st.sidebar.metric("Cevaplanan Soru", len(st.session_state.puanlar))

# Ana Ekran
if st.session_state.mevcut_soru:
    soru = st.session_state.mevcut_soru
    
    st.subheader(f"📌 Kategori: {soru['category']} ({soru['difficulty']})")
    st.info(f"**Mülakat Sorusu:** {soru['question']}")
    
    with st.expander("💡 Değerlendirme Kriterleri (İpucu)"):
        st.write("Bu soruda mülakatçının beklediği anahtar terimler:")
        for kp in soru.get("key_points", []):
            st.write(f"- {kp}")

    kullanici_cevabi = st.text_area("Cevabınızı yazın (Havacılık terimlerini ve kavramlarını kullanmaya özen gösterin):", height=150)

    col1, col2 = st.columns([1, 4])
    with col1:
        cevapla_btn = st.button("Cevabı Gönder", type="primary")
    with col2:
        if st.button("Bir Sonraki Soruya Geç ➔"):
            yeni_soru_getir()
            st.rerun()

    # Kural Tabanlı Otomatik Analiz (100 Üzerinden)
    if cevapla_btn:
        if not kullanici_cevabi.strip():
            st.warning("Lütfen önce bir cevap yazın!")
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

    if st.session_state.son_analiz:
        res = st.session_state.son_analiz
        puan = res["puan"]
        
        st.markdown("---")
        st.subheader("📋 Mülakat Değerlendirme Raporu")
        
        if puan >= 80:
            st.success(f"🏆 **Mülakat Puanı: {puan} / 100** — Harika! Konuya ve havacılık terminolojisine hakimsiniz.")
        elif puan >= 50:
            st.warning(f"⚠️ **Mülakat Puanı: {puan} / 100** — Geçer seviye. Bazı kilit kavramları unuttunuz.")
        else:
            st.error(f"❌ **Mülakat Puanı: {puan} / 100** — Yetersiz. Temel teknik terimleri tekrar gözden geçirmelisiniz.")

        c1, c2 = st.columns(2)
        with c1:
            st.markdown("### ✅ Yakalanan Anahtar Noktalar")
            if res["bulunanlar"]:
                for b in res["bulunanlar"]:
                    st.write(f"✔️ {b}")
            else:
                st.write("*Cevabınızda beklenen kilit kavramlar tespit edilemedi.*")

        with c2:
            st.markdown("### ❌ Eksik Kalan Noktalar")
            if res["bulunamayanlar"]:
                for ex in res["bulunamayanlar"]:
                    st.write(f"✖️ {ex}")
            else:
                st.write("*Tebrikler, tüm anahtar noktalar cevabınızda mevcut!*")
