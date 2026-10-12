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

# Kesin Aydınlık Mod ve Yüksek Kontrastlı Renk CSS'i
st.markdown("""
<style>
    /* Streamlit Genel Temasını Aydınlık Moda Zorlama */
    :root {
        --background-color: #f8fafc;
        --secondary-background-color: #ffffff;
        --text-color: #0f172a;
    }

    /* Ana Arka Plan */
    .stApp {
        background-color: #f8fafc !important;
        color: #0f172a !important;
    }

    /* Sol Menü (Sidebar) - Lacivert Zemin Üzerine Bembeyaz Okunur Yazılar */
    section[data-testid="stSidebar"] {
        background-color: #0b2559 !important;
    }
    section[data-testid="stSidebar"] *, 
    section[data-testid="stSidebar"] label, 
    section[data-testid="stSidebar"] p {
        color: #ffffff !important;
    }

    /* Selectbox (Kategori Seçim Kutusu) Düzeltmesi */
    div[data-baseweb="select"] > div {
        background-color: #ffffff !important;
        color: #0f172a !important;
        border: 1px solid #cbd5e1 !important;
        border-radius: 8px !important;
    }
    div[data-baseweb="select"] * {
        color: #0f172a !important;
    }

    /* Hero Banner */
    .hero-banner {
        background: linear-gradient(135deg, rgba(11, 37, 89, 0.95) 0%, rgba(29, 78, 216, 0.85) 100%), 
                    url('https://images.unsplash.com/photo-1540959733332-eab4deabeeaf?q=80&w=1200&auto=format&fit=crop');
        background-size: cover;
        background-position: center;
        border-radius: 16px;
        padding: 32px;
        color: #ffffff !important;
        margin-bottom: 24px;
        box-shadow: 0 8px 20px rgba(11, 37, 89, 0.12);
    }
    .hero-title {
        font-size: 2rem;
        font-weight: 700;
        margin-bottom: 6px;
        color: #ffffff !important;
    }
    .hero-subtitle {
        font-size: 1rem;
        color: #e2e8f0 !important;
        max-width: 600px;
        line-height: 1.5;
    }

    /* Soru Kartı */
    .main-card {
        background: #ffffff !important;
        border-radius: 16px;
        border: 1px solid #e2e8f0;
        padding: 24px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.04);
        margin-bottom: 16px;
    }
    .question-title {
        font-size: 1.25rem;
        font-weight: 700;
        color: #0f172a !important;
        margin-top: 12px;
        line-height: 1.5;
    }
    
    /* Kategori ve Zorluk Etiketleri (Badges) - Kalınlaştırılmış ve Renklendirilmiş */
    .badge-category {
        background-color: #dbeafe !important;
        color: #1e40af !important;
        border: 1.5px solid #93c5fd !important;
        padding: 6px 14px;
        border-radius: 20px;
        font-size: 0.9rem;
        font-weight: 800 !important;
        display: inline-block;
    }
    .badge-difficulty {
        background-color: #e2e8f0 !important;
        color: #1e293b !important;
        border: 1.5px solid #cbd5e1 !important;
        padding: 6px 14px;
        border-radius:
