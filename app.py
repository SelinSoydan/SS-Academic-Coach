import streamlit as st

from utils.auth import render_login_gate
from utils.bug_tracker import BugTracker
from utils.supabase_client import get_supabase_client
from utils.theme import inject_theme

st.set_page_config(page_title="SS Academic Coach", page_icon="🎓", layout="wide")
inject_theme()

client = get_supabase_client()

# Supabase yapılandırılmışsa giriş tüm sayfalar için zorunlu; değilse uygulama misafir modunda tam açılır
if client is not None and not render_login_gate(client, BugTracker(supabase_client=client)):
    st.stop()

nav = st.navigation([
    st.Page("views/home.py", title="Ana Sayfa", icon="🎓", default=True),
    st.Page("pages/0_Borusan_Equity_Cockpit.py", title="Borusan Equity Cockpit", icon="🏆", url_path="Borusan_Equity_Cockpit"),
    st.Page("pages/1_CFA_Research_Challenge.py", title="CFA Araştırma Masası", icon="📊", url_path="CFA_Research_Challenge"),
    st.Page("pages/3_SPL_Takas_Saklama_Koc.py", title="SPL Takas ve Saklama Koçu", icon="📘", url_path="SPL_Takas_Saklama_Koc"),
    st.Page("pages/2_Matematik_Programi.py", title="Finansal Modelleme Defteri", icon="🧮", url_path="Matematik_Programi"),
])
nav.run()
