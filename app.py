import datetime
import json
from pathlib import Path

import streamlit as st

from utils.auth import render_login_gate, sign_out
from utils.bug_tracker import BugTracker
from utils.supabase_client import get_supabase_client
from utils.theme import inject_theme

st.set_page_config(page_title="SS Academic Coach", page_icon="🎓", layout="wide")
inject_theme()

client = get_supabase_client()
bug_tracker = BugTracker(supabase_client=client)

# Supabase yapılandırılmışsa giriş zorunlu; değilse uygulama misafir modunda tam açılır
if client is not None and not render_login_gate(client, bug_tracker):
    st.stop()

DATA = Path(__file__).parent / "data"


def load(name: str) -> dict:
    try:
        return json.loads((DATA / name).read_text(encoding="utf-8"))
    except Exception as exc:
        bug_tracker.log(exc, context=f"home_load_{name}")
        return {}


lessons = load("spl_lessons/M01.json")
pitch = load("brsan_pitch.json")
bolumler = lessons.get("bolumler", [])
son_sayfa = bolumler[-1]["sayfa"].split("-")[-1] if bolumler else "?"

with st.sidebar:
    if client is not None and st.session_state.get("user"):
        st.write(f"👤 {st.session_state['user'].email}")
        if st.button("Çıkış Yap"):
            sign_out(client)
            st.rerun()
    else:
        st.caption("Misafir modu: tüm içerik açık, kişisel ilerleme kaydı için giriş gerekir.")
    st.markdown("---")
    st.header("🗓️ SPK Sınav Planlayıcı")
    exam_date = st.date_input("Yaklaşan SPK sınav tarihi", datetime.date(2026, 10, 2))
    target_hours = st.number_input("Hedef toplam çalışma saati", min_value=10, max_value=200, value=40)
    days_left = (exam_date - datetime.date.today()).days
    if days_left > 0:
        st.success(f"⏳ Kalan gün: {days_left}")
        st.metric("Günde çalışman gereken", f"{round(target_hours / days_left, 1)} saat")
    else:
        st.error("Sınav günü geldi ya da geçti.")

n_sources = len(pitch.get("sources", {}))
kpis = [
    ("CFA Research Challenge", "BRSAN", "Borusan Boru, Borsa İstanbul"),
    ("SPL 1012 modülü", f"{son_sayfa}/189 sayfa", f"{len(bolumler)} bölüm, sayfa sayfa işlendi"),
    ("SPL sınavına", f"{max(days_left, 0)} gün", exam_date.strftime("%d.%m.%Y")),
    ("Birincil kaynak", f"{n_sources} belge", "yatırımcı sunumları, EquityRT, CFA Institute"),
]
kpi_html = "".join(
    f'<div class="sac-kpi"><div class="l">{l}</div><div class="v">{val}</div><div class="s">{s}</div></div>'
    for l, val, s in kpis
)
st.markdown(
    '<div class="sac-hero">'
    '<div class="sac-eyebrow">Selin Soydan · Economics and Finance · İstanbul Bilgi Üniversitesi</div>'
    '<div class="sac-hero-title">SS Academic Coach</div>'
    '<div class="sac-hero-sub">Veriyi birincil kaynağından alan, hesabı açık formülle yapan ve öğrendiğini sınayan '
    'kişisel bir finans çalışma platformu. İçinde bir equity research masası, bir lisans sınavı koçu ve bir '
    'finansal modelleme defteri var.</div>'
    f'<div class="sac-kpi-grid">{kpi_html}</div></div>',
    unsafe_allow_html=True,
)

modules = [
    ("pages/0_Borusan_Equity_Cockpit.py", "🏆", "Borusan Equity Cockpit", "YENİ",
     "CFA Research Challenge değerleme masası: football field, duyarlılık tablosu, Monte Carlo, reverse DCF, "
     "risk matrisi, ESG ve jüri provası. Resmi CFA rubriğine göre kurgulandı."),
    ("pages/1_CFA_Research_Challenge.py", "📊", "CFA Araştırma Masası", "VERİ",
     "Şirket profili, ortaklık yapısı, canlı piyasa verisi, 14 şirketlik sektör karşılaştırması, "
     "dar peer grubu ve rasyo ansiklopedisi."),
    ("pages/3_SPL_Takas_Saklama_Koc.py", "📘", "SPL Takas, Saklama ve Operasyon", "SINAV",
     f"Resmi 1012 modülünün tamamı {len(bolumler)} bölümde: ana fikir, mantık, ezber, SPK'nın sevdiği sayılar, "
     "sınav tuzakları ve gerçek hayat bağlantısı."),
    ("pages/2_Matematik_Programi.py", "🧮", "Finansal Modelleme Defteri", "MATEMATİK",
     "Finansın arkasındaki matematik: basitten derine, etkileşimli panellerle ve çözülebilir öz testlerle."),
]
cols = st.columns(2)
for i, (path, icon, title, tag, desc) in enumerate(modules):
    with cols[i % 2]:
        st.markdown(
            f'<div class="sac-card"><span class="sac-pill">{tag}</span><h4>{icon} {title}</h4><p>{desc}</p></div>',
            unsafe_allow_html=True,
        )
        st.page_link(path, label=f"{title} sayfasını aç", icon="➡️")

st.markdown("#### Nasıl kuruldu")
layers = [
    ("1 · Kaynak", "Şirket yatırımcı sunumları, KAP bildirimleri, EquityRT ekranları, CFA Institute resmi belgeleri, SPL resmi ders kitabı."),
    ("2 · Veri", "Her rakam JSON dosyalarında kaynağı ve tarihiyle duruyor. Yeni çeyrek geldiğinde kod değil veri güncelleniyor."),
    ("3 · Hesap çekirdeği", "Değerleme formülleri Streamlit'ten bağımsız saf Python modülünde; birim testleriyle doğrulanıyor."),
    ("4 · Arayüz", "Streamlit çok sayfalı uygulama, Supabase kimlik doğrulama ve ilerleme kaydı, mobil uyumlu tema."),
    ("5 · Yayın", "GitHub deposundan Streamlit Community Cloud'a her commit ile otomatik dağıtım."),
]
lc = st.columns(len(layers))
for col, (t, d) in zip(lc, layers):
    col.markdown(f'<div class="sac-card"><h4 style="font-size:1.05rem">{t}</h4><p style="font-size:.82rem">{d}</p></div>', unsafe_allow_html=True)
st.caption("İlke: kaynağı gösterilemeyen hiçbir rakam uygulamaya girmez; eksik veri tahminle doldurulmaz, eksik olarak işaretlenir.")
