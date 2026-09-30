import streamlit as st

from utils.auth import render_login_gate
from utils.bug_tracker import BugTracker
from utils.i18n import L
from utils.supabase_client import get_supabase_client
from utils.theme import inject_theme

st.set_page_config(page_title="SS Academic Coach", page_icon="🎓", layout="wide")
inject_theme()

# Dil: paylaşılan link ?lang=EN taşıyorsa İngilizce açılır; sonra sayfanın üstündeki anahtar belirler
if "lang" not in st.session_state:
    st.session_state["lang"] = "EN" if st.query_params.get("lang") == "EN" else "TR"

client = get_supabase_client()

# Supabase yapılandırılmışsa giriş tüm sayfalar için zorunlu; değilse uygulama misafir modunda tam açılır
if client is not None and not render_login_gate(client, BugTracker(supabase_client=client)):
    st.stop()

home = st.Page("views/home.py", title=L("Ana Sayfa", "Home"), icon="🎓", default=True)
cockpit = st.Page("pages/0_Borusan_Equity_Cockpit.py", title="Borusan Equity Cockpit", icon="🏆", url_path="Borusan_Equity_Cockpit")
data_room = st.Page("pages/1_CFA_Research_Challenge.py", title=L("Veri Odası", "Data Room"), icon="🗂️", url_path="CFA_Research_Challenge")
spl = st.Page("pages/3_SPL_Takas_Saklama_Koc.py", title="SPL Takas ve Saklama Koçu", icon="📘", url_path="SPL_Takas_Saklama_Koc")
notebook = st.Page("pages/2_Matematik_Programi.py", title=L("Finansal Modelleme Defteri", "Financial Modelling Notebook"), icon="🧮", url_path="Matematik_Programi")
nav = st.navigation([home, cockpit, data_room, spl, notebook])

# İki dilli sayfalarda en üstte TR/EN anahtarı
if nav.title in (home.title, cockpit.title):
    def _flip_lang() -> None:
        st.session_state["lang"] = "EN" if st.session_state["_lang_toggle"] else "TR"

    _, right = st.columns([6, 1])
    right.toggle("🌐 English", value=st.session_state["lang"] == "EN", key="_lang_toggle", on_change=_flip_lang)

nav.run()
