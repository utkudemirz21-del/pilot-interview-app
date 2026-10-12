import json
import random
import requests
import streamlit as st
import google.generativeai as genai

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
st.write("Teknik havacılık bilginizi test edin ve yapay zekadan anlık mülakat geri bildirimi alın.")

# Yan Menü (Sidebar)
st.sidebar.header("⚙️ Yapay Zeka Ayarları")
provider = st.sidebar.radio("AI Sağlayıcı Seçin:", ["Google Gemini (Ücretsiz API)", "Ollama (Local)"])

gemini_key = ""
ollama_model = "llama3"

if provider == "Google Gemini (Ücretsiz API)":
    gemini_key = st.sidebar.text_input("Gemini API Key Girin:", type="password")
    st.sidebar.caption("aistudio.google.com adresinden ücretsiz alabilirsiniz.")
else:
    ollama_model = st.sidebar.text_input("Ollama Model Adı:", value="llama3")

# Kategori Seçimi
st.sidebar.header("🎯 Mülakat Konusu")
kategoriler = ["Tüm Kategoriler"] + list(set(q["category"] for q in questions_data)) if questions_data else []
secilen_kategori = st.sidebar.selectbox("Kategori Seçin:", kategoriler)

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
    st.sidebar.metric("Ortalama Puan", f"{ort:.1f} / 10")
    st.sidebar.metric("Cevaplanan Soru", len(st.session_state.puanlar))

# Ana Ekran
if st.session_state.mevcut_soru:
    soru = st.session_state.mevcut_soru
    
    st.subheader(f"📌 Kategori: {soru['category']} ({soru['difficulty']})")
    st.info(f"**Mülakat Sorusu:** {soru['question']}")
    
    with st.expander("💡 Değerlendirme Kriterleri (İpucu)"):
        st.write("Bu soruda mülakatçının beklediği anahtar noktalar:")
        for kp in soru.get("key_points", []):
            st.write(f"- {kp}")

    kullanici_cevabi = st.text_area("Cevabınızı buraya yazın (Havacılık terminolojisi kullanmaya özen gösterin):", height=150)

    col1, col2 = st.columns([1, 4])
    with col1:
        cevapla_btn = st.button("Cevabı Gönder", type="primary")
    with col2:
        if st.button("Bir Sonraki Soruya Geç ➔"):
            yeni_soru_getir()
            st.rerun()

    # AI Analizi
    if cevapla_btn:
        if not kullanici_cevabi.strip():
            st.warning("Lütfen önce bir cevap yazın!")
        else:
            prompt = f"""
            Sen tecrübeli bir Tip Eğitim Kaptanı ve Pilot Mülakatçısısın.
            
            Soru: {soru['question']}
            Beklenen Anahtar Noktalar: {', '.join(soru.get('key_points', []))}
            Adayın Cevabı: {kullanici_cevabi}
            
            Lütfen adayın cevabını bir pilot mülakatı standartlarında değerlendir.
            Yanıtını Türkçe ver ve şu yapıda olsun:
            
            1. PUAN: (0 ile 10 arasında sadece sayı)
            2. GÜÇLÜ YANLAR VE TERMİNOLOJİ: (Doğru kullanılan terimler ve bilgiler)
            3. EKSİK VEYA HATALI NOKTALAR: (Unutulan veya yanlış ifade edilen detaylar)
            4. İDEAL MÜLAKAT CEVABI: (Kısa, profesyonel kaptan yanıtı)
            """

            with st.spinner("Kaptan cevabınızı değerlendiriyor..."):
                analiz_metni = ""
                try:
                    if provider == "Google Gemini (Ücretsiz API)":
                        if not gemini_key:
                            st.error("Lütfen sol menüden Gemini API Key girin!")
                        else:
                            genai.configure(api_key=gemini_key)
                            model = genai.GenerativeModel('gemini-pro')
                            response = model.generate_content(prompt)
                            analiz_metni = response.text
                    else:
                        res = requests.post("http://localhost:11434/api/generate", json={
                            "model": ollama_model,
                            "prompt": prompt,
                            "stream": False
                        })
                        analiz_metni = res.json().get("response", "")

                    if analiz_metni:
                        st.session_state.son_analiz = analiz_metni
                        # Puanı çekmeye çalış
                        import re
                        match = re.search(r"PUAN:\s*(\d+)", analiz_metni)
                        if match:
                            st.session_state.puanlar.append(int(match.group(1)))

                except Exception as e:
                    st.error(f"Değerlendirme sırasında bir hata oluştu: {e}")

    if st.session_state.son_analiz:
        st.markdown("---")
        st.subheader("📋 Mülakatçı Geri Bildirimi")
        st.write(st.session_state.son_analiz)
    
