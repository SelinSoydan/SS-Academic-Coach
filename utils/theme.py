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
    ".sac-hero{background:radial-gradient(circle at 88% 12%,rgba(255,214,236,0.35) 0,rgba(255,214,236,0) 38%),linear-gradient(125deg,#3B2338 0%,#6E3A63 52%,#B9548A 100%);color:#FFF;border-radius:26px;padding:28px 30px 22px;margin:4px 0 18px;box-shadow:0 14px 40px rgba(74,46,69,0.28);}",
    ".sac-eyebrow{font-size:.74rem;letter-spacing:.14em;text-transform:uppercase;opacity:.82;font-weight:600;}",
    ".sac-hero-title{font-family:'Cormorant Garamond',Georgia,serif;font-size:2.6rem;font-weight:700;line-height:1.1;margin:6px 0 4px;color:#FFF;}",
    ".sac-hero-title span{font-family:'Quicksand',sans-serif;font-size:.95rem;font-weight:600;background:rgba(255,255,255,0.16);border:1px solid rgba(255,255,255,0.3);border-radius:999px;padding:3px 12px;margin-left:10px;vertical-align:middle;}",
    ".sac-hero-sub{opacity:.9;font-size:.95rem;margin-bottom:16px;max-width:780px;}",
    ".sac-kpi-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;}",
    ".sac-kpi{background:rgba(255,255,255,0.1);border:1px solid rgba(255,255,255,0.22);border-radius:16px;padding:10px 13px;}",
    ".sac-kpi .l{font-size:.72rem;opacity:.8;font-weight:600;}",
    ".sac-kpi .v{font-size:1.45rem;font-weight:700;margin:2px 0;}",
    ".sac-kpi .s{font-size:.66rem;opacity:.7;}",
    ".sac-card{background:#FFF;border:1px solid #F0D5E6;border-radius:18px;padding:16px 18px;box-shadow:0 6px 18px rgba(194,87,139,0.07);height:100%;margin-bottom:10px;}",
    ".sac-card h4{font-family:'Cormorant Garamond',Georgia,serif;color:var(--sac-plum);font-size:1.3rem;margin:4px 0 6px;}",
    ".sac-card p{font-size:.9rem;color:#4F3F4B;margin:0 0 6px;}",
    ".sac-pill{display:inline-block;padding:2px 10px;border-radius:999px;background:#F6E4F2;color:#7B3F6E;font-size:.7rem;font-weight:700;letter-spacing:.03em;}",
    ".sac-pill.green{background:#E3F4EC;color:#2F6F55;}",
    ".sac-pill.amber{background:#FDF0DC;color:#8A5A12;}",
    ".sac-src{font-size:.7rem;color:#8A6A82;margin-top:4px;}",
    ".sac-big{font-family:'Cormorant Garamond',Georgia,serif;font-size:2rem;font-weight:700;color:#7B3F6E;line-height:1.1;}",
    ".sac-thesis{background:linear-gradient(120deg,#FFF,#FBEFF7);border-left:5px solid var(--sac-pink);border-radius:14px;padding:14px 18px;margin:8px 0 14px;font-size:1.02rem;color:var(--sac-plum);}",
    ".sac-tl{border-left:2px solid #E7C9DD;margin-left:6px;padding-left:16px;}",
    ".sac-tl-item{position:relative;margin-bottom:12px;}",
    ".sac-tl-item:before{content:'';position:absolute;left:-23px;top:4px;width:12px;height:12px;border-radius:50%;background:var(--sac-pink);box-shadow:0 0 0 3px #FBE3F0;}",
    ".sac-tl-item.future:before{background:#FFF;border:2px solid var(--sac-pink);}",
    ".sac-tl-date{font-size:.74rem;font-weight:700;color:#9A5A87;}",
])

_CSS = f"<style>{_FONT_IMPORT}{_CSS_RULES}</style>"


def inject_theme() -> None:
    st.markdown(_CSS, unsafe_allow_html=True)


def banner(text: str) -> None:
    st.markdown(f'<div class="sac-banner">🌸 {text}</div>', unsafe_allow_html=True)
