import streamlit as st

_FONT_IMPORT = (
    "@import url('https://fonts.googleapis.com/css2?"
    "family=Cormorant+Garamond:wght@600;700&family=Quicksand:wght@400;500;600;700&display=swap');"
)

_CSS_RULES = "".join([
    ":root{--sac-pink:#C2578B;--sac-pink-soft:#F6E4F2;--sac-lavender:#EDE3F7;--sac-plum:#4A2E45;}",
    "html,body,[class*='css']{font-family:'Quicksand',sans-serif;}",
    "h1,h2,h3{font-family:'Cormorant Garamond',Georgia,serif !important;color:var(--sac-plum) !important;}",
    "[data-testid='stAppViewContainer']{background:linear-gradient(160deg,#FFF8FB 0%,#FBF0F8 45%,#F3E6F5 100%);}",
    "[data-testid='stSidebar']{background:linear-gradient(180deg,#F9E9F3 0%,#EFE1F4 100%);border-right:1px solid #E7C9DD;}",
    "[data-testid='stHeader']{background:rgba(255,255,255,0);}",
    "div[data-testid='stMetric']{background:#FFFFFF;border:1px solid #F0D5E6;border-radius:18px;padding:14px 16px;box-shadow:0 4px 14px rgba(194,87,139,0.08);}",
    "div.stButton > button, div.stFormSubmitButton > button{border-radius:999px !important;border:1px solid var(--sac-pink) !important;background:linear-gradient(135deg,#E58FB3,#C2578B) !important;color:white !important;font-weight:600 !important;box-shadow:0 3px 10px rgba(194,87,139,0.25);}",
    "div.stButton > button:hover{filter:brightness(1.06);}",
    ".stTabs [data-baseweb='tab-list']{gap:4px;}",
    ".stTabs [data-baseweb='tab']{background-color:#FBEFF7;border-radius:14px 14px 0 0;padding:8px 16px;}",
    ".stTabs [aria-selected='true']{background-color:var(--sac-pink-soft) !important;color:var(--sac-plum) !important;font-weight:700;}",
    "div[data-testid='stExpander']{border:1px solid #F0D5E6;border-radius:16px;background:#FFFDFE;}",
    ".sac-banner{background:linear-gradient(120deg,#FBE3F0,#F1E1F7);border:1px solid #EFCBE0;border-radius:20px;padding:14px 20px;margin-bottom:14px;font-family:'Cormorant Garamond',serif;font-size:1.05rem;color:var(--sac-plum);}",
])

_CSS = f"<style>{_FONT_IMPORT}{_CSS_RULES}</style>"


def inject_theme() -> None:
    st.markdown(_CSS, unsafe_allow_html=True)


def banner(text: str) -> None:
    st.markdown(f'<div class="sac-banner">🌸 {text}</div>', unsafe_allow_html=True)
