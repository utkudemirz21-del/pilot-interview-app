import streamlit as st
import json
import re

# Page Config
st.set_page_config(page_title="ATPL Mülakat Koçu", page_icon="✈️", layout="wide")

# 1. Türkçe Harf Dönüştürücü (Karakter hatalarını önler)
def turkish_lower(text: str) -> str:
    if not text:
        return ""
    rep = {'I': 'ı', 'İ': 'i', 'Ç': 'ç', 'Ş': 'ş', 'Ğ': 'ğ', 'Ü': 'ü', 'Ö': 'ö'}
    for search, replace in rep.items():
        text = text.replace(search, replace)
    return text.lower()

# 2. Gerçek Key-Word Karşılaştırma ve Puanlama Algoritması
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
        clean_kw = turkish_lower(str(kw).strip())
        if clean_kw and clean_kw in clean_answer:
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

# 3. JSON Sorularını Yükle
@st.cache_data
def load_questions():
    try:
        with open("questions.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        st.error(f"questions.json dosyası yüklenemedi: {e}")
        return []

all_questions = load_questions()

# Header
st.title("✈️ Pilot Teknik Mülakat Hazırlık Modülü")
st.write("Cevabınızdaki anahtar kelime (keyword) sayısına göre skorlama yapılır.")

if not all_questions:
    st.error("Soru verisi bulunamadı. Lütfen questions.json dosyasını kontrol edin.")
    st.stop()

# --- SIDEBAR FİLTRELERİ ---
st.sidebar.title("🎯 Filtreler & Ayarlar")

selected_difficulty = st.sidebar.multiselect(
    "Zorluk Derecesi:",
    options=["Kolay", "Orta", "Zor"],
    default=["Kolay", "Orta", "Zor"]
)

all_categories = sorted(list(set(q.get("category", "Genel") for q in all_questions)))
selected_categories = st.sidebar.multiselect(
    "Kategori:",
    options=all_categories,
    default=all_categories
)

# Filtreleme
filtered_questions = [
    q for q in all_questions
    if q.get("difficulty", "Orta") in selected_difficulty
    and q.get("category", "Genel") in selected_categories
]

st.sidebar.write(f"Mevcut Soru Sayısı: **{len(filtered_questions)}**")

if not filtered_questions:
    st.warning("Seçilen filtrelere uygun soru bulunamadı. Lütfen sidebar'dan seçim yapın.")
    st.stop()

# --- SORU SEÇİMİ VE SESSION STATE ---
if "question_index" not in st.session_state:
    st.session_state.question_index = 0

# İndex sınır kontrolü
if st.session_state.question_index >= len(filtered_questions):
    st.session_state.question_index = 0

col_nav1, col_nav2, col_nav3 = st.columns([1, 4, 1])
with col_nav1:
    if st.button("⬅️ Önceki Soru"):
        st.session_state.question_index = (st.session_state.question_index - 1) % len(filtered_questions)
        st.rerun()

with col_nav3:
    if st.button("Sonraki Soru ➡️"):
        st.session_state.question_index = (st.session_state.question_index + 1) % len(filtered_questions)
        st.rerun()

soru = filtered_questions[st.session_state.question_index]

st.divider()

# --- EKRAN GÖSTERİMİ ---
st.markdown(f"### ❓ Soru {soru.get('id', '')}: {soru.get('question', '')}")

col_m1, col_m2 = st.columns(2)
with col_m1:
    st.info(f"📁 **Kategori:** {soru.get('category', 'Genel')}")
with col_m2:
    st.warning(f"🎯 **Zorluk:** {soru.get('difficulty', 'Orta')}")

# 💡 İPUCU ALANI
with st.expander("💡 İpucu Göster"):
    kws = soru.get("keywords", [])
    if kws:
        st.write("Bu soruda aranacak bazı temel kavramlar:")
        st.write(f"👉 **{', '.join(kws[:2])}** ...")
    else:
        st.write("Bu soru için özel ipucu yok.")

# CEVAP ALANI
user_input = st.text_area(
    "Yanıtınızı buraya yazınız:", 
    height=140, 
    key=f"input_{soru.get('id')}"
)

if st.button("Cevabı Değerlendir", type="primary", key=f"btn_{soru.get('id')}"):
    if user_input.strip():
        result = calculate_score(user_input, soru.get("keywords", []))
        score = result["score"]
        
        st.markdown("---")
        st.subheader("📊 Değerlendirme Sonucu")
        
        if score == 100:
            st.success(f"🎉 **100 Puan (Tam Uygun)** - Yakalanan Keyword: {result['matched_count']}")
        elif score == 80:
            st.info(f"🟡 **80 Puan (İyi)** - Yakalanan Keyword: {result['matched_count']}")
        elif score == 60:
            st.warning(f"🟠 **60 Puan (Orta)** - Yakalanan Keyword: {result['matched_count']}")
        elif score == 30:
            st.error(f"🔴 **30 Puan (Zayıf)** - Yakalanan Keyword: {result['matched_count']}")
        else:
            st.error(f"❌ **0 Puan (Yetersiz)** - Yanıtınızda anahtar kelime bulunamadı.")

        res_col1, res_col2 = st.columns(2)
        with res_col1:
            st.markdown("#### ✅ Yakalanan Kelimeler")
            if result["matched_keywords"]:
                for kw in result["matched_keywords"]:
                    st.success(f"• {kw}")
            else:
                st.write("*Hiçbiri yakalanamadı.*")

        with res_col2:
            st.markdown("#### ❌ Kaçırılan Kelimeler")
            if result["missing_keywords"]:
                for kw in result["missing_keywords"]:
                    st.error(f"• {kw}")
            else:
                st.write("*Tüm kelimeler yakalandı!*")
    else:
        st.warning("Lütfen değerlendirilmesi için bir metin girin.")
