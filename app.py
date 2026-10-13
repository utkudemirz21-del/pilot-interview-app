import json
import random
import re
import io
import html
import streamlit as st
import speech_recognition as sr
from audio_recorder_streamlit import audio_recorder
from supabase import create_client, Client

# Sayfa Yapılandırması
st.set_page_config(
    page_title="PilotInterviewPro",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- SUPABASE BAĞLANTISI VE OTURUM YÖNETİMİ ---
@st.cache_resource
def init_supabase() -> Client:
    url = st.secrets.get("SUPABASE_URL", "")
    key = st.secrets.get("SUPABASE_KEY", "")
    if not url or not key:
        return None
    return create_client(url, key)

supabase = init_supabase()

# 🎨 TASARIM SİSTEMİ — "Flight Deck"
# Palet : Gece paneli #0A1626 · Harita kâğıdı #EDF0F4 · Mürekkep #0E1A2B
#         Kehribar (uyarı lambası) #F2A81D · Enstrüman yeşili #2FBF8F · Alarm kırmızısı #D8483F · Gökyüzü #3C7DD9
# Yazı  : Barlow Semi Condensed (başlık / sayısal okumalar, hava yolu tabelası havası) + IBM Plex Sans (metin)
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Barlow+Semi+Condensed:wght@500;600;700&family=IBM+Plex+Sans:wght@400;500;600&display=swap');

    :root {
        --panel: #0A1626;
        --panel-2: #12263F;
        --panel-line: #223A5A;
        --paper: #EDF0F4;
        --card: #FFFFFF;
        --ink: #0E1A2B;
        --ink-soft: #55657A;
        --line: #D5DBE4;
        --amber: #F2A81D;
        --amber-deep: #B97A00;
        --green: #2FBF8F;
        --red: #D8483F;
        --sky: #3C7DD9;
    }

    html, body, [class*="css"] { font-family: 'IBM Plex Sans', sans-serif; }
    h1, h2, h3, h4, .display { font-family: 'Barlow Semi Condensed', sans-serif !important; letter-spacing: 0.1px; }

    .stApp { background: var(--paper) !important; color: var(--ink) !important; }
    header[data-testid="stHeader"] { background: transparent !important; }
    footer, #MainMenu { visibility: hidden; }
    .block-container { padding-top: 2rem; max-width: 1280px; }

    /* ---------- Yan panel (kokpit paneli) ---------- */
    section[data-testid="stSidebar"] {
        background: var(--panel) !important;
        border-right: 1px solid var(--panel-line);
    }
    section[data-testid="stSidebar"] label p,
    section[data-testid="stSidebar"] label { color: #C9D6E8 !important; font-weight: 500 !important; }
    section[data-testid="stSidebar"] hr { border-color: var(--panel-line) !important; }
    section[data-testid="stSidebar"] .stButton button {
        background: transparent !important;
        color: #E6EEF8 !important;
        border: 1px solid var(--panel-line) !important;
        border-radius: 8px !important;
        font-weight: 500;
    }
    section[data-testid="stSidebar"] .stButton button:hover {
        border-color: var(--amber) !important;
        color: var(--amber) !important;
    }
    .side-brand { padding: 6px 0 14px 0; }
    .side-brand .name { font-family: 'Barlow Semi Condensed', sans-serif; font-weight: 700; font-size: 1.55rem; color: #fff; line-height: 1.1; }
    .side-brand .name span { color: var(--amber); }
    .side-brand .who { color: #8FA8C8; font-size: 0.82rem; margin-top: 6px; word-break: break-all; }
    .side-stat { display:flex; justify-content:space-between; align-items:baseline; padding: 8px 0; border-bottom: 1px solid var(--panel-line); color:#8FA8C8; font-size:0.85rem; }
    .side-stat b { color:#fff; font-family:'Barlow Semi Condensed',sans-serif; font-size:1.15rem; font-weight:600; }

    /* ---------- Hero ---------- */
    .hero {
        position: relative; overflow: hidden;
        background: var(--panel);
        border-radius: 14px;
        padding: 36px 40px 40px 40px;
        margin-bottom: 20px;
        color: #fff;
        animation: heroIn .7s cubic-bezier(.16,1,.3,1) both;
    }
    .hero::before { /* ufuk çizgisi + irtifa çentikleri */
        content: ''; position: absolute; inset: 0;
        background:
            linear-gradient(180deg, transparent 0 58%, rgba(60,125,217,.22) 58.2%, rgba(60,125,217,.06) 100%),
            repeating-linear-gradient(90deg, rgba(255,255,255,.07) 0 1px, transparent 1px 48px);
        pointer-events: none;
    }
    .hero::after { /* sağda kehribar kılavuz çizgisi */
        content: ''; position: absolute; right: 40px; top: 0; bottom: 0; width: 3px;
        background: linear-gradient(180deg, var(--amber), rgba(242,168,29,0));
        opacity: .9;
    }
    .hero > * { position: relative; z-index: 1; }
    .hero .title { font-family:'Barlow Semi Condensed',sans-serif; font-size: 2.7rem; font-weight: 700; line-height: 1.05; margin: 0 0 10px 0; }
    .hero .sub { color: #B9C9DE; font-size: 1.02rem; max-width: 620px; line-height: 1.6; }
    .welcome { display:flex; align-items:center; gap:14px; margin-bottom: 22px; }
    .welcome .avatar {
        width: 46px; height: 46px; border-radius: 50%;
        background: var(--amber); color: #1A1203;
        display:flex; align-items:center; justify-content:center;
        font-family:'Barlow Semi Condensed',sans-serif; font-weight:700; font-size: 1.35rem;
        flex-shrink: 0;
    }
    .welcome .hi { color:#8FA8C8; font-size: 0.85rem; line-height: 1.2; }
    .welcome .name { font-family:'Barlow Semi Condensed',sans-serif; font-weight:600; font-size: 1.45rem; color:#fff; line-height: 1.2; }
    .hero.center { text-align: center; }
    .hero.center .sub { margin: 0 auto; }
    @keyframes heroIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: none; } }

    /* ---------- Enstrüman şeridi (özet metrikler) ---------- */
    .strip {
        display: grid; grid-template-columns: repeat(4, 1fr);
        background: var(--card); border: 1px solid var(--line); border-radius: 12px;
        margin-bottom: 22px; overflow: hidden;
    }
    .strip .cell { padding: 16px 20px; border-right: 1px solid var(--line); }
    .strip .cell:last-child { border-right: none; }
    .strip .k { color: var(--ink-soft); font-size: 0.8rem; margin-bottom: 4px; }
    .strip .v { font-family:'Barlow Semi Condensed',sans-serif; font-size: 1.9rem; font-weight: 600; color: var(--ink); line-height: 1.1; font-variant-numeric: tabular-nums; }
    .strip .v small { font-size: 0.95rem; color: var(--ink-soft); font-weight: 500; margin-left: 4px; }

    /* ---------- Soru kartı (briefing) ---------- */
    .brief {
        background: var(--card);
        border: 1px solid var(--line);
        border-left: 5px solid var(--amber);
        border-radius: 12px;
        padding: 26px 30px;
        margin-bottom: 22px;
    }
    .tags { display:flex; gap:8px; align-items:center; flex-wrap:wrap; margin-bottom: 14px; }
    .tag-cat { background: var(--panel); color:#fff; border-radius: 6px; padding: 5px 12px; font-size: 0.82rem; font-weight: 500; }
    .tag-diff { border-radius: 6px; padding: 5px 12px; font-size: 0.82rem; font-weight: 600; border: 1px solid; }
    .tag-diff.kolay { color:#13795B; border-color:#9ADBC4; background:#EAF8F2; }
    .tag-diff.orta  { color:#8A5B00; border-color:#F2D18A; background:#FEF6E1; }
    .tag-diff.zor   { color:#A82F28; border-color:#EFB1AC; background:#FDEEEC; }
    .q-text { font-family:'Barlow Semi Condensed',sans-serif; font-size: 1.7rem; font-weight: 600; color: var(--ink); line-height: 1.3; max-width: 760px; }

    /* ---------- Mikrofon paneli ---------- */
    .st-key-mic_card {
        background: var(--card);
        border: 1px solid var(--line);
        border-radius: 12px;
        padding: 18px 22px 8px 22px;
        margin-bottom: 18px;
    }
    .mic-h { font-family:'Barlow Semi Condensed',sans-serif; font-weight:600; font-size:1.15rem; color:var(--ink); }
    .mic-s { color: var(--ink-soft); font-size: 0.88rem; margin: 2px 0 10px 0; }

    /* ---------- Form elemanları ---------- */
    .stTextArea label p { font-weight: 600; color: var(--ink); }
    .stTextArea textarea {
        background: var(--card) !important; color: var(--ink) !important;
        border: 1.5px solid var(--line) !important; border-radius: 10px !important;
        padding: 14px 16px !important; font-size: 1rem !important; line-height: 1.55;
    }
    .stTextArea textarea:focus { border-color: var(--sky) !important; box-shadow: 0 0 0 3px rgba(60,125,217,.18) !important; }
    .stTextInput input { border-radius: 10px !important; }

    .stButton button { border-radius: 10px; font-weight: 600; padding: 0.55rem 1rem; transition: background .15s, border-color .15s; }
    .stButton button[kind="primary"], .stButton button[data-testid="stBaseButton-primary"] {
        background: var(--amber) !important; color: #1A1203 !important; border: 1px solid var(--amber) !important;
    }
    .stButton button[kind="primary"]:hover, .stButton button[data-testid="stBaseButton-primary"]:hover {
        background: #FFBD3A !important; border-color: #FFBD3A !important; color:#1A1203 !important;
    }
    .stButton button[kind="secondary"], .stButton button[data-testid="stBaseButton-secondary"] {
        background: var(--card); color: var(--ink); border: 1.5px solid var(--line);
    }
    .stButton button[kind="secondary"]:hover, .stButton button[data-testid="stBaseButton-secondary"]:hover {
        border-color: var(--ink); color: var(--ink);
    }
    button:focus-visible { outline: 3px solid var(--sky) !important; outline-offset: 2px; }

    /* ---------- Karne (skor göstergesi) ---------- */
    .report {
        background: var(--card); border: 1px solid var(--line); border-radius: 12px;
        padding: 26px 30px; margin-top: 8px; margin-bottom: 22px;
        display: grid; grid-template-columns: 220px 1fr; gap: 28px; align-items: center;
    }
    .gauge { text-align: center; }
    .gauge svg { width: 100%; max-width: 220px; height: auto; display:block; margin: 0 auto; }
    .gauge .num { font-family:'Barlow Semi Condensed',sans-serif; font-size: 2.6rem; font-weight: 700; fill: var(--ink); }
    .gauge .of  { font-size: 0.8rem; fill: var(--ink-soft); }
    .verdict .label { font-family:'Barlow Semi Condensed',sans-serif; font-size: 1.6rem; font-weight: 700; margin-bottom: 4px; }
    .verdict .desc { color: var(--ink-soft); line-height: 1.55; margin-bottom: 14px; }
    .chips { display:flex; flex-wrap:wrap; gap:6px; margin-top: 6px; }
    .chips-title { font-size: 0.8rem; color: var(--ink-soft); margin-top: 10px; font-weight: 600; }
    .chip { border-radius: 6px; padding: 4px 10px; font-size: 0.82rem; font-weight: 500; border: 1px solid; }
    .chip.ok   { color:#13795B; background:#EAF8F2; border-color:#9ADBC4; }
    .chip.miss { color:#7A5A12; background:#FEF6E1; border-color:#F2D18A; }

    .model-answer {
        background: var(--panel); color: #E6EEF8; border-radius: 12px;
        padding: 22px 28px; margin-bottom: 22px; border-left: 5px solid var(--green);
    }
    .model-answer .h { font-family:'Barlow Semi Condensed',sans-serif; font-weight:600; font-size:1.05rem; color: var(--green); margin-bottom: 8px; }
    .model-answer .t { line-height: 1.7; font-size: 1rem; max-width: 760px; }

    /* ---------- İpucu ---------- */
    .tip {
        background: transparent; border: 1px dashed #B5C0CF; border-radius: 12px;
        padding: 16px 22px; color: var(--ink-soft); font-size: 0.92rem; line-height: 1.6;
    }
    .tip b { color: var(--ink); }

    /* ---------- Uçuş ilerlemesi ---------- */
    .flight {
        background: var(--card); border: 1px solid var(--line); border-radius: 12px; padding: 22px 24px;
    }
    .flight .h { font-family:'Barlow Semi Condensed',sans-serif; font-weight:600; font-size:1.1rem; color: var(--ink); margin-bottom: 14px; }
    .flight .pct { font-family:'Barlow Semi Condensed',sans-serif; font-size: 2.6rem; font-weight: 700; color: var(--ink); line-height: 1; font-variant-numeric: tabular-nums; }
    .flight .track { position: relative; height: 4px; background: var(--line); border-radius: 4px; margin: 22px 8px 10px 8px; }
    .flight .fill  { position:absolute; left:0; top:0; bottom:0; background: var(--amber); border-radius: 4px; }
    .flight .dot   { position:absolute; top:50%; width: 16px; height: 16px; border-radius: 50%; background: var(--panel); border: 3px solid var(--amber); transform: translate(-50%, -50%); }
    .flight .end   { position:absolute; right:-8px; top:50%; width: 10px; height: 10px; background: var(--ink); transform: translateY(-50%) rotate(45deg); }
    .flight .legend { display:flex; justify-content:space-between; color: var(--ink-soft); font-size: 0.8rem; margin: 0 4px; }
    .flight .note { margin-top: 14px; color: var(--ink-soft); font-size: 0.9rem; line-height: 1.5; }
    .flight .note b { color: var(--ink); }

    @media (max-width: 800px) {
        .strip { grid-template-columns: repeat(2, 1fr); }
        .strip .cell:nth-child(2) { border-right: none; }
        .strip .cell:nth-child(-n+2) { border-bottom: 1px solid var(--line); }
        .report { grid-template-columns: 1fr; }
        .hero { padding: 26px 22px 30px 22px; }
        .hero .title { font-size: 2rem; }
        .q-text { font-size: 1.35rem; }
    }
    @media (prefers-reduced-motion: reduce) { .hero { animation: none; } }
</style>
""", unsafe_allow_html=True)

# Helper Fonksiyonlar
def turkish_lower(text: str) -> str:
    if not text: return ""
    rep = {'I': 'ı', 'İ': 'i', 'Ç': 'ç', 'Ş': 'ş', 'Ğ': 'ğ', 'Ü': 'ü', 'Ö': 'ö'}
    for search, replace in rep.items(): text = text.replace(search, replace)
    return text.lower()

def transcribe_audio(audio_bytes):
    recognizer = sr.Recognizer()
    try:
        audio_file = io.BytesIO(audio_bytes)
        with sr.AudioFile(audio_file) as source:
            audio_data = recognizer.record(source)
            return recognizer.recognize_google(audio_data, language="tr-TR")
    except Exception:
        return ""

def is_flexible_match(keyword: str, clean_answer: str) -> bool:
    clean_kw = turkish_lower(str(keyword).strip())
    clean_kw = re.sub(r'[^\w\s]', '', clean_kw)
    if not clean_kw: return False
    if clean_kw in clean_answer: return True
    words_in_kw = clean_kw.split()
    if len(words_in_kw) > 1:
        matched_parts = sum(1 for w in words_in_kw if len(w) >= 3 and (w[:4] if len(w) >= 4 else w) in clean_answer)
        return matched_parts >= 1
    else:
        single_w = words_in_kw[0]
        return (single_w[:4] in clean_answer) if len(single_w) >= 4 else (single_w in clean_answer)

def calculate_score(user_answer: str, keywords: list) -> dict:
    if not user_answer or not user_answer.strip():
        return {"score": 0, "matched_count": 0, "matched_keywords": [], "missing_keywords": keywords}
    clean_answer = re.sub(r'[^\w\s]', ' ', turkish_lower(user_answer))
    matched_keywords = [kw for kw in keywords if is_flexible_match(kw, clean_answer)]
    missing_keywords = [kw for kw in keywords if kw not in matched_keywords]
    match_count = len(matched_keywords)
    score = 100 if match_count >= 4 else (80 if match_count == 3 else (60 if match_count == 2 else (30 if match_count == 1 else 0)))
    return {"score": score, "matched_count": match_count, "matched_keywords": matched_keywords, "missing_keywords": missing_keywords}

@st.cache_data(ttl=60)
def load_questions():
    try:
        with open("questions.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

questions_data = load_questions()

# Session State Başlatma
if "user" not in st.session_state: st.session_state.user = None
if "session" not in st.session_state: st.session_state.session = None
if "sorulan_ids" not in st.session_state: st.session_state.sorulan_ids = []
if "puanlar" not in st.session_state: st.session_state.puanlar = []
if "mevcut_soru" not in st.session_state: st.session_state.mevcut_soru = None
if "son_analiz" not in st.session_state: st.session_state.son_analiz = None
if "secilen_kategori" not in st.session_state: st.session_state.secilen_kategori = "Tüm Kategoriler"
if "last_processed_audio" not in st.session_state: st.session_state.last_processed_audio = None

# SUPABASE KONTROLÜ VE OTURUMU GERİ YÜKLEME
if supabase and not st.session_state.user:
    try:
        curr_session = supabase.auth.get_session()
        if curr_session and curr_session.user:
            st.session_state.user = curr_session.user
            st.session_state.session = curr_session
    except Exception:
        pass

def save_user_progress():
    if supabase and st.session_state.user:
        try:
            supabase.table("user_progress").upsert({
                "user_id": st.session_state.user.id,
                "email": st.session_state.user.email,
                "sorulan_ids": st.session_state.sorulan_ids,
                "puanlar": st.session_state.puanlar
            }).execute()
        except Exception:
            pass

def load_user_progress():
    if supabase and st.session_state.user:
        try:
            res = supabase.table("user_progress").select("*").eq("user_id", st.session_state.user.id).execute()
            if res.data and len(res.data) > 0:
                data = res.data[0]
                st.session_state.sorulan_ids = data.get("sorulan_ids", []) or []
                st.session_state.puanlar = data.get("puanlar", []) or []
        except Exception:
            pass

def reset_user_progress():
    st.session_state.sorulan_ids = []
    st.session_state.puanlar = []
    st.session_state.son_analiz = None
    save_user_progress()

def puan_kaydet(soru_id, puan):
    # Her soru için tek puan: aynı soru tekrar değerlendirilirse son puanı günceller, yeni kayıt eklemez.
    an = st.session_state.son_analiz
    if an and an.get("soru_id") == soru_id and st.session_state.puanlar:
        st.session_state.puanlar[-1] = puan
    else:
        st.session_state.puanlar.append(puan)

# --- GÖRSEL YARDIMCILAR (sadece UI) ---
SKOR_BILGI = {
    100: ("Mükemmel", "#2FBF8F", "Yanıtınız beklenen cevapla tam uyumlu. Bu seviyeyi koruyun."),
    80:  ("Çok iyi", "#2FBF8F", "Yanıtınız büyük oranda yeterli. Eksik kalan kavramları ekleyerek 100'e çıkabilirsiniz."),
    60:  ("Orta seviye", "#F2A81D", "Temel fikir var ancak bazı önemli detaylar eksik kaldı."),
    30:  ("Zayıf", "#D8483F", "Doğru yanıttan uzak kalındı. Örnek cevabı okuyup tekrar deneyin."),
    0:   ("Yetersiz", "#D8483F", "Hedeflenen açıklamalar yanıtınızda bulunamadı."),
}

def gauge_svg(puan: int, renk: str) -> str:
    # Yarım daire ibreli gösterge: yay uzunluğu = pi * 80
    uzunluk = 251.33
    dolu = uzunluk * (puan / 100)
    return f"""
    <svg viewBox="0 0 200 124" role="img" aria-label="Skor {puan} / 100">
        <path d="M20 104 A80 80 0 0 1 180 104" fill="none" stroke="#E3E8EF" stroke-width="14" stroke-linecap="round"/>
        <path d="M20 104 A80 80 0 0 1 180 104" fill="none" stroke="{renk}" stroke-width="14" stroke-linecap="round"
              stroke-dasharray="{dolu:.1f} {uzunluk:.1f}"/>
        <text x="100" y="92" text-anchor="middle" class="num">{puan}</text>
        <text x="100" y="114" text-anchor="middle" class="of">/ 100</text>
    </svg>"""

def chips_html(items, css_class):
    return "".join(f'<span class="chip {css_class}">{k}</span>' for k in items)

# --- GİRİŞ / KAYIT EKRANI ---
if not st.session_state.user:
    st.markdown("""
    <div class="hero center">
        <div class="title">✈️ PilotInterviewPro</div>
        <div class="sub">Havayolu mülakatına teknik sorularla hazırlanın. İlerlemeniz hesabınızda saklanır.</div>
    </div>
    """, unsafe_allow_html=True)

    col_auth1, col_auth2, col_auth3 = st.columns([1, 1.6, 1])
    with col_auth2:
        tab_login, tab_signup = st.tabs(["Giriş yap", "Kayıt ol"])

        with tab_login:
            login_email = st.text_input("E-posta", key="l_email")
            login_pass = st.text_input("Şifre", type="password", key="l_pass")
            if st.button("Giriş yap", type="primary", use_container_width=True):
                if supabase:
                    try:
                        res = supabase.auth.sign_in_with_password({"email": login_email, "password": login_pass})
                        st.session_state.user = res.user
                        st.session_state.session = res.session
                        load_user_progress()
                        st.success("Giriş başarılı!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Giriş hatası: {e}")
                else:
                    st.error("Supabase bağlantı bilgileri eksik (Secrets).")

        with tab_signup:
            signup_email = st.text_input("E-posta", key="s_email")
            signup_pass = st.text_input("Şifre (en az 6 karakter)", type="password", key="s_pass")
            if st.button("Hesap oluştur", use_container_width=True):
                if supabase:
                    try:
                        res = supabase.auth.sign_up({"email": signup_email, "password": signup_pass})
                        st.session_state.user = res.user
                        st.session_state.session = res.session
                        save_user_progress()
                        st.success("Hesabınız oluşturuldu!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Kayıt hatası: {e}")
    st.stop()

# Oturum Açık ise İlerlemeyi Yükle (İlk Yüklemede)
if st.session_state.user and not st.session_state.sorulan_ids and not st.session_state.puanlar:
    load_user_progress()

# --- GİRİŞ YAPILDIKTAN SONRAKİ UYGULAMA AKIŞI ---

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
        save_user_progress()

# Hesaplamalar (yan panel ve ana ekran ortak kullanır)
toplam_soru = len(questions_data)
tamamlanan = len(st.session_state.puanlar)
ort_skor = (sum(st.session_state.puanlar) / tamamlanan) if tamamlanan > 0 else 0

# Sidebar
st.sidebar.markdown(f"""
<div class="side-brand">
    <div class="name">✈️ Pilot<span>Interview</span>Pro</div>
    <div class="who">{st.session_state.user.email}</div>
</div>
""", unsafe_allow_html=True)

kategoriler = ["Tüm Kategoriler"] + sorted(list(set(q["category"] for q in questions_data))) if questions_data else []

def on_kategori_change():
    yeni_kat = st.session_state.kat_select_box
    st.session_state.secilen_kategori = yeni_kat
    yeni_soru_getir(yeni_kat)

kat_index = kategoriler.index(st.session_state.secilen_kategori) if st.session_state.secilen_kategori in kategoriler else 0

secilen_kategori = st.sidebar.selectbox("Mülakat kategorisi", kategoriler, index=kat_index, key="kat_select_box", on_change=on_kategori_change)

st.sidebar.markdown(f"""
<div style="margin-top:14px;">
    <div class="side-stat"><span>Yanıtlanan</span><b>{tamamlanan}</b></div>
    <div class="side-stat"><span>Ortalama skor</span><b>%{ort_skor:.0f}</b></div>
    <div class="side-stat"><span>Hedef</span><b>%80+</b></div>
</div>
""", unsafe_allow_html=True)

st.sidebar.markdown("<div style='height:18px'></div>", unsafe_allow_html=True)

if st.sidebar.button("İlerlemeyi sıfırla", use_container_width=True, help="Tüm yanıt ve puan geçmişinizi sıfırlar."):
    reset_user_progress()
    st.rerun()

if st.sidebar.button("Çıkış yap", use_container_width=True):
    if supabase:
        try:
            supabase.auth.sign_out()
        except Exception:
            pass
    st.session_state.user = None
    st.session_state.session = None
    st.session_state.sorulan_ids = []
    st.session_state.puanlar = []
    st.rerun()

if st.session_state.mevcut_soru is None and questions_data:
    yeni_soru_getir(st.session_state.secilen_kategori)

# Kullanıcı adı (e-postanın @ öncesi kısmından türetilir)
def display_name(email: str) -> str:
    local = (email or "").split("@")[0]
    words = [w for w in re.split(r"[._\-\s]+", local) if w]
    out = []
    for w in words:
        first = "İ" if w[0] == "i" else ("I" if w[0] == "ı" else w[0].upper())
        out.append(first + turkish_lower(w[1:]))
    return " ".join(out) if out else "Pilot Adayı"

kullanici_adi = display_name(st.session_state.user.email)
avatar_harf = html.escape(kullanici_adi[0])
kullanici_adi_html = html.escape(kullanici_adi)

# Hero Banner
st.markdown(f"""
<div class="hero">
    <div class="welcome">
        <div class="avatar">{avatar_harf}</div>
        <div>
            <div class="hi">Hoş geldiniz</div>
            <div class="name">{kullanici_adi_html}</div>
        </div>
    </div>
    <div class="title">Pilot mülakatına hazırlanın</div>
    <div class="sub">Teknik sorulara sesle yanıt verin, havacılık terminolojisini net kullanın. İlerlemeniz hesabınıza otomatik kaydedilir.</div>
</div>
""", unsafe_allow_html=True)

# Enstrüman şeridi
st.markdown(f"""
<div class="strip">
    <div class="cell"><div class="k">Toplam soru</div><div class="v">{toplam_soru}</div></div>
    <div class="cell"><div class="k">Kategori</div><div class="v">{max(len(kategoriler)-1, 0)}</div></div>
    <div class="cell"><div class="k">Ortalama skor</div><div class="v">%{ort_skor:.0f}</div></div>
    <div class="cell"><div class="k">Hedef skor</div><div class="v">%80<small>ve üzeri</small></div></div>
</div>
""", unsafe_allow_html=True)

col_left, col_right = st.columns([2.5, 1], gap="large")

with col_left:
    if st.session_state.mevcut_soru:
        soru = st.session_state.mevcut_soru
        input_key = f"answer_input_{soru.get('id')}"

        zorluk = soru.get('difficulty', 'Orta')
        zorluk_css = {"Kolay": "kolay", "Orta": "orta", "Zor": "zor"}.get(zorluk, "orta")

        st.markdown(f"""
        <div class="brief">
            <div class="tags">
                <span class="tag-cat">{soru.get('category', 'Genel')}</span>
                <span class="tag-diff {zorluk_css}">{zorluk}</span>
            </div>
            <div class="q-text">{soru.get('question', '')}</div>
        </div>
        """, unsafe_allow_html=True)

        # MODEL / DOĞRU CEVAP CÜMLEMİZİ HAZIRLAMA
        model_answer_text = soru.get("model_answer")
        if not model_answer_text:
            kw_list = soru.get("keywords", [])
            model_answer_text = "Bu soru için mülakatta açıklanması beklenen temel konu: " + ", ".join(kw_list) + " kavramlarının doğru usullerle ifade edilmesidir."

        # MİKROFON PANELİ (key => .st-key-mic_card ile stillenir)
        with st.container(key="mic_card"):
            st.markdown("""
            <div class="mic-h">Sesli yanıt</div>
            <div class="mic-s">Mikrofona basıp konuşun. 5 saniye sessizlik olursa yanıt otomatik değerlendirilir.</div>
            """, unsafe_allow_html=True)
            audio_bytes = audio_recorder(
                text="Mikrofona bas ve konuş",
                recording_color="#D8483F",
                neutral_color="#0A1626",
                icon_name="microphone",
                icon_size="2x",
                pause_threshold=5.0,
                key=f"rec_{soru.get('id')}_{len(st.session_state.sorulan_ids)}"
            )

        if audio_bytes and audio_bytes != st.session_state.last_processed_audio:
            st.session_state.last_processed_audio = audio_bytes
            with st.spinner("Ses çözümleniyor ve değerlendiriliyor..."):
                transcribed_text = transcribe_audio(audio_bytes)
                if transcribed_text.strip():
                    st.session_state[input_key] = transcribed_text
                    keywords = soru.get("keywords", [])
                    eval_result = calculate_score(transcribed_text, keywords)
                    puan = eval_result["score"]
                    puan_kaydet(soru.get("id"), puan)
                    st.session_state.son_analiz = {
                        "soru_id": soru.get("id"),
                        "puan": puan,
                        "metin": transcribed_text,
                        "model_answer": model_answer_text,
                        "matched": eval_result["matched_keywords"],
                        "missing": eval_result["missing_keywords"],
                    }
                    save_user_progress()
                    st.rerun()
                else:
                    st.warning("Ses anlaşılamadı. Mikrofona yakın konuşup tekrar deneyin ya da yanıtı aşağıya yazın.")

        kullanici_cevabi = st.text_area("Algılanan / yazılan yanıtınız", placeholder="Konuştuğunuzda metin buraya yazılır. İsterseniz elle de düzenleyebilirsiniz.", height=130, key=input_key)

        btn_c1, btn_c2 = st.columns([1, 1])
        with btn_c1:
            if st.button("Yanıtı değerlendir", type="primary", use_container_width=True):
                if kullanici_cevabi.strip():
                    keywords = soru.get("keywords", [])
                    eval_result = calculate_score(kullanici_cevabi, keywords)
                    puan = eval_result["score"]
                    puan_kaydet(soru.get("id"), puan)
                    st.session_state.son_analiz = {
                        "soru_id": soru.get("id"),
                        "puan": puan,
                        "metin": kullanici_cevabi,
                        "model_answer": model_answer_text,
                        "matched": eval_result["matched_keywords"],
                        "missing": eval_result["missing_keywords"],
                    }
                    save_user_progress()
                    st.rerun()
                else:
                    st.warning("Önce bir yanıt söyleyin veya yazın.")

        with btn_c2:
            if st.button("Sonraki soru", use_container_width=True):
                yeni_soru_getir(st.session_state.secilen_kategori)
                st.rerun()

        if st.session_state.son_analiz:
            res = st.session_state.son_analiz
            puan = res["puan"]
            etiket, renk, aciklama = SKOR_BILGI.get(puan, SKOR_BILGI[0])

            matched = res.get("matched", [])
            missing = res.get("missing", [])
            kw_html = ""
            if matched:
                kw_html += f'<div class="chips-title">Yanıtınızda geçen kavramlar</div><div class="chips">{chips_html(matched, "ok")}</div>'
            if missing:
                kw_html += f'<div class="chips-title">Eklenebilecek kavramlar</div><div class="chips">{chips_html(missing, "miss")}</div>'

            st.markdown(f"""
            <div class="report">
                <div class="gauge">{gauge_svg(puan, renk)}</div>
                <div class="verdict">
                    <div class="label" style="color:{renk};">{etiket}</div>
                    <div class="desc">{aciklama}</div>
                    {kw_html}
                </div>
            </div>
            <div class="model-answer">
                <div class="h">Mülakatta beklenen örnek cevap</div>
                <div class="t">{res.get('model_answer', '')}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("""
    <div class="tip">
        <b>Mülakat ipucu:</b> Sistemlerin çalışmasını anlatırken <b>neden-sonuç ilişkisini</b> ve standart operasyon usullerini (SOP) vurgulamak puanınızı artırır.
    </div>
    """, unsafe_allow_html=True)

with col_right:
    yuzde = min(int((tamamlanan / toplam_soru) * 100), 100) if toplam_soru > 0 else 0
    st.markdown(f"""
    <div class="flight">
        <div class="h">Uçuş ilerlemesi</div>
        <div class="pct">%{yuzde}</div>
        <div class="track">
            <div class="fill" style="width:{yuzde}%;"></div>
            <div class="dot" style="left:{yuzde}%;"></div>
            <div class="end"></div>
        </div>
        <div class="legend"><span>Kalkış</span><span>Varış</span></div>
        <div class="note">Toplam <b>{toplam_soru}</b> sorudan <b>{tamamlanan}</b> tanesi yanıtlandı.</div>
    </div>
    """, unsafe_allow_html=True)
