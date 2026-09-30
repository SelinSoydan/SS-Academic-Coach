import datetime
import json
from pathlib import Path

import streamlit as st

from utils.auth import sign_out
from utils.bug_tracker import BugTracker
from utils.i18n import L
from utils.supabase_client import get_supabase_client

client = get_supabase_client()
bug_tracker = BugTracker(supabase_client=client)

DATA = Path(__file__).parent.parent / "data"


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
    ("CFA Research Challenge", "BRSAN", L("Borusan Boru, Borsa İstanbul", "Borusan Boru, Borsa Istanbul")),
    (L("SPL 1012 modülü", "SPL module 1012"), L(f"{len(bolumler)} bölüm", f"{len(bolumler)} chapters"),
     L(f"ders sayfaları 1 ile {son_sayfa} arası eksiksiz", f"lesson pages 1 to {son_sayfa}, complete")),
    (L("SPL sınavına", "SPL exam in"), L(f"{max(days_left, 0)} gün", f"{max(days_left, 0)} days"), exam_date.strftime("%d.%m.%Y")),
    (L("Birincil kaynak", "Primary sources"), L(f"{n_sources} belge", f"{n_sources} documents"),
     L("yatırımcı sunumları, EquityRT, CFA Institute", "investor decks, EquityRT, CFA Institute")),
]
kpi_html = "".join(
    f'<div class="sac-kpi"><div class="l">{l}</div><div class="v">{val}</div><div class="s">{s}</div></div>'
    for l, val, s in kpis
)
st.markdown(
    '<div class="sac-hero">'
    '<div class="sac-eyebrow">Selin Soydan · Economics and Finance · ' + L("İstanbul Bilgi Üniversitesi", "Istanbul Bilgi University") + '</div>'
    '<div class="sac-hero-title">SS Academic Coach</div>'
    '<div class="sac-hero-sub">' + L(
        "Veriyi birincil kaynağından alan, hesabı açık formülle yapan ve öğrendiğini sınayan kişisel bir finans çalışma platformu. "
        "İçinde bir equity research masası, bir veri odası, bir lisans sınavı koçu ve bir finansal modelleme defteri var.",
        "A personal finance study platform that takes data from primary sources, calculates with open formulas and tests what it teaches. "
        "It holds an equity research desk, a data room, a licensing exam coach and a financial modelling notebook.") + '</div>'
    f'<div class="sac-kpi-grid">{kpi_html}</div></div>',
    unsafe_allow_html=True,
)

modules = [
    ("pages/0_Borusan_Equity_Cockpit.py", "🏆", "Borusan Equity Cockpit", L("ANALİZ", "ANALYSIS"),
     L("CFA Research Challenge değerleme masası: football field, duyarlılık, Monte Carlo, reverse DCF, risk matrisi, ESG, jüri provası "
       "ve beş kişilik takım için ortak Takım Masası. Resmi CFA rubriğine göre kurgulandı.",
       "The CFA Research Challenge valuation desk: football field, sensitivity, Monte Carlo, reverse DCF, risk matrix, ESG, jury rehearsal "
       "and a shared Team Desk for a five person team. Built around the official CFA rubric.")),
    ("pages/1_CFA_Research_Challenge.py", "🗂️", L("Veri Odası", "Data Room"), L("VERİ", "DATA"),
     L("Ham veri ve kaynaklar: şirket profili, ortaklık yapısı, haberler, canlı piyasa verisi, EquityRT Excel yükleme, "
       "14 şirketlik sektör karşılaştırması ve rasyo ansiklopedisi. Analiz Cockpit'te, veri burada.",
       "Raw data and sources: company profile, ownership, news, live market data, EquityRT Excel upload, a 14 company sector "
       "comparison and the ratio encyclopedia. Analysis lives in the Cockpit, data lives here.")),
    ("pages/3_SPL_Takas_Saklama_Koc.py", "📘", L("SPL Takas, Saklama ve Operasyon", "SPL Clearing, Custody and Operations"), L("SINAV", "EXAM"),
     L(f"Resmi 1012 modülünün tamamı {len(bolumler)} bölümde: ana fikir, mantık, ezber, SPK'nın sevdiği sayılar, sınav tuzakları ve gerçek hayat bağlantısı.",
       f"The full official module 1012 in {len(bolumler)} chapters, in Turkish: key idea, logic, what to memorise, the numbers the regulator likes, exam traps and real world links.")),
    ("pages/2_Matematik_Programi.py", "🧮", L("Finansal Modelleme Defteri", "Financial Modelling Notebook"), L("MATEMATİK", "MATHS"),
     L("Finansın arkasındaki matematik: basitten derine, etkileşimli panellerle ve çözülebilir öz testlerle.",
       "The maths behind finance: from simple to deep, with interactive panels and self tests.")),
]
cols = st.columns(2)
for i, (path, icon, title, tag, desc) in enumerate(modules):
    with cols[i % 2]:
        st.markdown(
            f'<div class="sac-card"><span class="sac-pill">{tag}</span><h4>{icon} {title}</h4><p>{desc}</p></div>',
            unsafe_allow_html=True,
        )
        st.page_link(path, label=L(f"{title} sayfasını aç", f"Open {title}"), icon="➡️")

st.markdown("#### " + L("Nasıl kuruldu", "How it is built"))
layers = [
    (L("1 · Kaynak", "1 · Source"), L("Şirket yatırımcı sunumları, KAP bildirimleri, EquityRT ekranları, CFA Institute resmi belgeleri, SPL resmi ders kitabı.",
                                    "Company investor decks, KAP disclosures, EquityRT screens, official CFA Institute documents, the official SPL textbook.")),
    (L("2 · Veri", "2 · Data"), L("Her rakam JSON dosyalarında kaynağı ve tarihiyle duruyor. Yeni çeyrek geldiğinde kod değil veri güncelleniyor.",
                                "Every figure sits in JSON files with its source and date. When a new quarter arrives, the data changes, not the code.")),
    (L("3 · Hesap çekirdeği", "3 · Calculation core"), L("Değerleme formülleri Streamlit'ten bağımsız saf Python modülünde; birim testleriyle doğrulanıyor.",
                                                       "Valuation formulas live in a pure Python module independent of Streamlit and are verified by unit tests.")),
    (L("4 · Arayüz", "4 · Interface"), L("Çok sayfalı Streamlit uygulaması, iki dil, canlı Takım Masası, paylaşılabilir senaryo linkleri, mobil uyumlu tema.",
                                       "A multi page Streamlit app, two languages, a live Team Desk, shareable scenario links, a mobile friendly theme.")),
    (L("5 · Yayın", "5 · Delivery"), L("GitHub deposundan Streamlit Community Cloud'a her commit ile otomatik dağıtım.",
                                     "Automatic deployment from the GitHub repository to Streamlit Community Cloud on every commit.")),
]
lc = st.columns(len(layers))
for col, (t, d) in zip(lc, layers):
    col.markdown(f'<div class="sac-card"><h4 style="font-size:1.05rem">{t}</h4><p style="font-size:.82rem">{d}</p></div>', unsafe_allow_html=True)
st.caption(L("İlke: kaynağı gösterilemeyen hiçbir rakam uygulamaya girmez; eksik veri tahminle doldurulmaz, eksik olarak işaretlenir.",
             "Principle: no figure enters the app unless its source can be shown; missing data is flagged as missing, never filled with a guess."))
