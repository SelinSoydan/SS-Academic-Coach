from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="Matematik Programı", page_icon="📐", layout="wide")

st.title("📐 Matematik Programı — Quant Hazırlık")
st.caption(
    "Yüksek lisans (AI x Finans) ve ekonometri için gereken matematiği sıfırdan işleyen, "
    "ders ders büyüyen interaktif defter. Log/türev, Σ/varyans/kovaryans, regresyon tekrarı "
    "ile başlıyor; sıradaki ders matris cebri."
)
st.caption("Ayrıca bağımsız olarak burada da yayında: https://selinsoydan.github.io/finansal-modelleme-defteri/")

NOTEBOOK_PATH = Path(__file__).parent.parent / "matematik-defteri" / "index.html"

if NOTEBOOK_PATH.exists():
    html = NOTEBOOK_PATH.read_text(encoding="utf-8")
    components.html(html, height=1400, scrolling=True)
else:
    st.error("matematik-defteri/index.html bulunamadı.")
