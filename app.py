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

# 🎨 MODERN UI & ANİMASYON CSS KODLARI
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

    * {
        font-family: 'Inter', sans-serif;
    }

    /* Sayfa Arka Planı */
    .stApp { 
        background-color: #f1f5f9 !important; 
        color: #0f172a !important; 
    }
    
    /* Fade In & Slide Up Animasyonu */
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

    /* Sol Menü (Sidebar) */
    section[data-testid="stSidebar"] { 
        background-color: #0b1e36 !important; 
        border-right: 1px solid #1e293b;
    }
    section[data-testid="stSidebar"] label { 
        color: #f8fafc !important; 
        font-weight: 600 !important; 
    }

    /* Modern Hero Banner */
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

    /* Modern Soru Kartı */
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
    
    /* Rozetler */
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

    /* Text Area */
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

    /* Sağ Panel Kartı */
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

    /* Metrik Kartları Özelleştirme */
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

# 🛠️ ESNEK SKORLAMA
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
        Teknik bilginizi sesle veya yazarak anında test edin.
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
        
        # Soru Kartı (Animasyonlu)
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

        st.write("### 📝 Cevap Alanı")

        # 🎙️ ANİMASYONLU SES KONTROLÜ (HTML / CSS ANİMASYONLARI DÂHİL)
        speech_control_html = """
        <style>
            @keyframes pulse-red {
                0% { box-shadow: 0 0 0 0 rgba(225, 29, 72, 0.4); }
                70% { box-shadow: 0 0 0 10px rgba(225, 29, 72, 0); }
                100% { box-shadow: 0 0 0 0 rgba(225, 29, 72, 0); }
            }
            .recording-active {
                animation: pulse-red 1.5s infinite;
                background-color: #e11d48 !important;
            }
            .btn-voice {
                transition: all 0.2s ease;
            }
            .btn-voice:hover {
                transform: scale(1.02);
            }
        </style>

        <div style="background: #ffffff; padding: 14px 18px; border-radius: 16px; border: 1px solid #e2e8f0; margin-bottom: 12px; display: flex; align-items: center; gap: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.02);">
            <button id="start-btn" class="btn-voice" type="button" style="background-color: #2563eb; color: white; border: none; padding: 10px 20px; font-weight: 700; border-radius: 10px; cursor: pointer; font-size: 14px;">
                🎙️ Konuşmayı Başlat
            </button>
            <button id="stop-btn" class="btn-voice" type="button" style="background-color: #f1f5f9; color: #475569; border: 1px solid #cbd5e1; padding: 10px 20px; font-weight: 700; border-radius: 10px; cursor: pointer; font-size: 14px;">
                🛑 Durdur
            </button>
            <span id="status" style="font-weight: 600; font-size: 14px; color: #64748b; margin-left: 6px;">Mikrofon Hazır</span>
        </div>

        <script>
            const startBtn = document.getElementById('start-btn');
            const stopBtn = document.getElementById('stop-btn');
            const status = document.getElementById('status');

            const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

            if (!SpeechRecognition) {
                status.innerText = "Tarayıcınız ses tanımayı desteklemiyor (Chrome/Edge kullanın).";
                status.style.color = "#ef4444";
            } else {
                const recognition = new SpeechRecognition();
                recognition.lang = 'tr-TR';
                recognition.continuous = true;
                recognition.interimResults = true;

                let timer = null;

                function resetTimer() {
                    clearTimeout(timer);
                    timer = setTimeout(() => {
                        recognition.stop();
                        status.innerText = "5 sn sessizlik nedeniyle kayıt tamamlandı.";
                        status.style.color = "#d97706";
                        startBtn.classList.remove('recording-active');
                    }, 5000);
                }

                recognition.onstart = () => {
                    status.innerText = "🔴 Dinleniyor... (Konuşabilirsiniz)";
                    status.style.color = "#e11d48";
                    startBtn.classList.add('recording-active');
                    resetTimer();
                };

                recognition.onresult = (event) => {
                    resetTimer();
                    let transcript = '';
                    for (let i = 0; i < event.results.length; i++) {
                        transcript += event.results[i][0].transcript;
                    }
                    
                    try {
                        const parentTextareas = window.parent.document.querySelectorAll('textarea');
                        if (parentTextareas.length > 0) {
                            const target = parentTextareas[0];
                            const nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, "value").set;
                            nativeInputValueSetter.call(target, transcript);
                            target.dispatchEvent(new Event('input', { bubbles: true }));
                        }
                    } catch (e) {
                        console.log("Hata:", e);
                    }
                };

                recognition.onerror = (event) => {
                    status.innerText = "Mikrofon hatası: " + event.error;
                    status.style.color = "#ef4444";
                    startBtn.classList.remove('recording-active');
                };

                recognition.onend = () => {
                    clearTimeout(timer);
                    startBtn.classList.remove('recording-active');
                    if (!status.innerText.includes("sessizlik")) {
                        status.innerText = "✅ Ses Aktarıldı";
                        status.style.color = "#16a34a";
                    }
                };

                startBtn.onclick = () => recognition.start();
                stopBtn.onclick = () => recognition.stop();
            }
        </script>
        """
        components.html(speech_control_html, height=80)

        # TEXTAREA
        kullanici_cevabi = st.text_area(
            "Cevabınız:",
            placeholder="Cevabınızı buraya yazabilir veya mikrofona basarak konuşabilirsiniz...",
            height=150,
            key=f"text_input_{soru.get('id')}"
        )

        btn_c1, btn_c2 = st.columns([1, 1])
        with btn_c1:
            cevapla_btn = st.button("💾 Yanıtı Kaydet ve Değerlendir", type="primary", use_container_width=True)
        with btn_c2:
            if st.button("Sonraki Soru ➔", use_container_width=True):
                yeni_soru_getir(st.session_state.secilen_kategori)
                st.rerun()

        if cevapla_btn:
            if not kullanici_cevabi.strip():
                st.warning("⚠️ Lütfen değerlendirme yapabilmek için cevabınızı metin alanına yazın veya konuşarak doldurun.")
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

# SADELEŞTİRİLMİŞ SAĞ PANEL (Sadece İlerleme Göstergesi)
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
