import streamlit as st
import json
import re

# 1. Türkçe Harf Dönüştürücü (Karakter hatasını önler)
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

    # Kullanıcı yanıtını temizle
    clean_answer = turkish_lower(user_answer)
    clean_answer = re.sub(r'[^\w\s]', ' ', clean_answer)  # Noktalamaları temizle

    matched_keywords = []
    missing_keywords = []

    # Her bir keyword'ü tek tek kullanıcı cevabında ara
    for kw in keywords:
        clean_kw = turkish_lower(str(kw).strip())
        
        # Tam kelime veya kelime öbeği eşleşmesi kontrolü
        if clean_kw and clean_kw in clean_answer:
            matched_keywords.append(kw)
        else:
            missing_keywords.append(kw)

    match_count = len(matched_keywords)

    # Katı Puanlama Kuralları
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

# --- KULLANICI ARAYÜZÜ VE İPUCU ALANI ---

# Aktif soruyu al (Örnek: session_state veya listeden)
soru = st.session_state.get("current_question", filtered_questions[0] if 'filtered_questions' in locals() and filtered_questions else None)

if soru:
    # Soru Bilgileri
    st.markdown(f"### ❓ Soru {soru.get('id', '')}: {soru.get('question', '')}")
    
    col_info1, col_info2 = st.columns(2)
    with col_info1:
        st.info(f"📁 **Kategori:** {soru.get('category', 'Genel')}")
    with col_info2:
        st.warning(f"🎯 **Zorluk:** {soru.get('difficulty', 'Orta')}")

    # 💡 İPUCU ALANI (Açılır İpucu Kutusu)
    with st.expander("💡 İpucu Göster / Gizle"):
        st.write("Bu soruda aranacak kavramlardan bazıları:")
        # İlk 2 keyword'ü ipucu olarak gösterir, cevabı tamamen ifşa etmez
        sample_hints = soru.get("keywords", [])[:2]
        if sample_hints:
            st.markdown(f"👉 *Harf/Kavram ipuçları:* **{', '.join(sample_hints)}**")
        else:
            st.write("Bu soru için özel ipucu bulunmuyor.")

    # CEVAP GİRDİ ALANI
    user_input = st.text_area("Cevabınızı buraya yazın:", height=150, key=f"input_{soru.get('id')}")

    if st.button("Cevabı Değerlendir", key=f"btn_{soru.get('id')}"):
        if user_input.strip():
            result = calculate_score(user_input, soru.get("keywords", []))
            
            # Puan Gösterimi
            score = result["score"]
            st.divider()
            
            if score == 100:
                st.balloons()
                st.success(f"🎉 Mükemmel! Puanınız: **{score}** (Eşleşen Keyword: {result['matched_count']})")
            elif score == 80:
                st.info(f"👍 Çok İyi! Puanınız: **{score}** (Eşleşen Keyword: {result['matched_count']})")
            elif score == 60:
                st.warning(f"⚠️ Orta! Puanınız: **{score}** (Eşleşen Keyword: {result['matched_count']})")
            elif score == 30:
                st.error(f"🔴 Zayıf! Puanınız: **{score}** (Eşleşen Keyword: {result['matched_count']})")
            else:
                st.error(f"❌ Yetersiz! Puanınız: **0** (Hiçbir anahtar kelime bulunamadı)")

            # Keyword Detay Tablosu
            res_col1, res_col2 = st.columns(2)
            with res_col1:
                st.markdown("### ✅ Yakalanan Kelimeler")
                if result["matched_keywords"]:
                    for kw in result["matched_keywords"]:
                        st.success(f"• {kw}")
                else:
                    st.write("*Hiçbiri yakalanamadı.*")

            with res_col2:
                st.markdown("### ❌ Kaçırılan Kelimeler")
                if result["missing_keywords"]:
                    for kw in result["missing_keywords"]:
                        st.error(f"• {kw}")
                else:
                    st.write("*Tüm kelimeler yakalandı!*")
        else:
            st.warning("Lütfen değerlendirmek için bir cevap metni girin.")
