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

# 🛠️ TÜRKÇE HARF DÖNÜŞTÜRÜCÜ
def turkish_lower(text: str) -> str:
    if not text:
        return ""
    rep = {'I': 'ı', 'İ': 'i', 'Ç': 'ç', 'Ş': 'ş', 'Ğ': 'ğ', 'Ü': 'ü', 'Ö': 'ö'}
    for search, replace in rep.items():
        text = text.replace(search, replace)
    return text.lower()

# 🛠️ GEVŞETİLMİŞ VE ESNEK (STEM / FUZZY) KELİME EŞLEŞTİRME MOTORU
def is_flexible_match(keyword: str, clean_answer: str) -> bool:
    clean_kw = turkish_lower(str(keyword).strip())
    clean_kw = re.sub(r'[^\w\s]', '', clean_kw)  # Noktalamaları temizle
    
    if not clean_kw:
        return False

    # 1. Birebir Tam Eşleşme veya Alt Cümle
    if clean_kw in clean_answer:
        return True

    # 2. Türkçe Kök / Gövde Yakalama (Kelime 4 harften uzunsa ilk 4-5 harfi kontrol et)
    words_in_kw = clean_kw.split()
    
    # Çoklu kelimeler için (Örn: "süzülüş hattı", "point of no return")
    if len(words_in_kw) > 1:
        # Anahtar kelimedeki en az 1 ana kelime cevapta geçiyor mu?
        matched_parts = 0
        for w in words_in_kw:
            if len(w) >= 3:
                stem = w[:4] if len(w) >= 4 else w
                if stem in clean_answer:
                    matched_parts += 1
        if matched_parts >= 1:  # En az 1 parçası geçiyorsa esnek kabul et
            return True
    else:
        # Tekli kelimeler için (Örn: "altimetre" -> "altimetrenin", "altimetreye")
        single_w = words_in_kw[0]
        if len(single_w) >= 4:
            stem = single_w[:4]  # İlk 4 harf kök kabul edilir
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

    # 🎯 GEVŞETİLMİŞ PUAN KURALI
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

st.markdown("""
<div class="hero-banner">
    <div class="hero-title">Pilot Mülakatına Hazırlanın</div>
    <div class="hero-subtitle">
        Gerçek mülakat deneyimini simüle eden sorularla kendinizi geliştirin. 
        Teknik bilginizi ister sesinizle ister yazarak test edin.
    </div>
</div>
""", unsafe_allow_html=True)

toplam_soru = len(questions_data)
tamamlanan = len(st.session_state.puanlar)
ort_skor = (sum(st.session_state.puanlar) / tamamlanan) if tamamlanan > 0 else 0

st1, st2, st3, st4 = st.columns(4)
st1.metric("Toplam Soru", f"{toplam_soru}+")
st2.metric("Kategori", f"{len(kategoriler)-1} Başlık")
st3.metric("Ortalama Skor", f"%{ort_skor:.0f}")
st4.metric("Seviye", "ATPL & CPL")

st.markdown("<br>", unsafe_allow_html=True)

col_left, col_right = st.columns([2.3, 1])

with col_left:
    if st.session_state.mevcut_soru:
        soru = st.session_state.mevcut_soru
        
        st.markdown(f"""
        <div class="main-card">
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

        st.write("### 📝 Cevap Alanı (Sesli veya Yazılı)")
        st.caption("İster mikrofona basıp konuşun, ister klavye ile doğrudan yazın.")

        # HTML/JS Ses Kontrol Bileşeni
        speech_control_html = """
        <div style="background: #ffffff; padding: 12px; border-radius: 12px; border: 1px solid #cbd5e1; margin-bottom: 12px; display: flex; align-items: center; gap: 10px;">
            <button id="start-btn" type="button" style="background-color: #2563eb; color: white; border: none; padding: 8px 16px; font-weight: bold; border-radius: 8px; cursor: pointer; font-size: 14px;">
                🎙️ Konuşmayı Başlat
            </button>
            <button id="stop-btn" type="button" style="background-color: #ef4444; color: white; border: none; padding: 8px 16px; font-weight: bold; border-radius: 8px; cursor: pointer; font-size: 14px;">
                🛑 Durdur
            </button>
            <span id="status" style="font-weight: bold; font-size: 14px; color: #64748b;">Mikrofon Hazır</span>
        </div>

        <script>
            const startBtn = document.getElementById('start-btn');
            const stopBtn = document.getElementById('stop-btn');
            const status = document.getElementById('status');

            const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

            if (!SpeechRecognition) {
                status.innerText = "Tarayıcınız ses tanımayı desteklemiyor (Chrome/Edge kullanın).";
                status.style.color = "red";
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
                    }, 5000);
                }

                recognition.onstart = () => {
                    status.innerText = "🔴 Dinleniyor... (Konuşabilirsiniz)";
                    status.style.color = "#e11d48";
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
                    status.style.color = "red";
                };

                recognition.onend = () => {
                    clearTimeout(timer);
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
        components.html(speech_control_html, height=75)

        # TEXTAREA ALANI
        kullanici_cevabi = st.text_area(
            "Cevabınız:",
            placeholder="Cevabınızı buraya yazabilir veya yukarıdaki mikrofona basarak konuşabilirsiniz...",
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
