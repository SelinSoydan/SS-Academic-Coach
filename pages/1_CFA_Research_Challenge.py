import datetime

import streamlit as st

from utils.bug_tracker import BugTracker
from utils.supabase_client import get_supabase_client

st.set_page_config(page_title="CFA Research Challenge", page_icon="📊", layout="wide")

client = get_supabase_client()
bug_tracker = BugTracker(supabase_client=client)

DEADLINE = datetime.date(2026, 9, 28)
REPORT_SECTIONS = [
    "Executive Summary & Recommendation",
    "Business Description",
    "Industry Overview & Competitive Positioning",
    "Investment Summary (thesis)",
    "Valuation (DCF + comps, triangulated)",
    "Financial Analysis",
    "Risks",
    "Corporate Governance & ESG",
    "Appendix / model exhibits",
]

TARGET_COMPANY = "Borusan"

st.title("📊 CFA Research Challenge")
st.caption(f"Hedef şirket: {TARGET_COMPANY}")

days_left = (DEADLINE - datetime.date.today()).days
if days_left >= 0:
    st.error(f"⏳ Son başvuru tarihine {days_left} gün kaldı — {DEADLINE.strftime('%d %B %Y')}")
else:
    st.warning("Son başvuru tarihi geçti.")

tab_report, tab_dcf, tab_comps = st.tabs(
    ["📝 Rapor İlerleme Takibi", "💰 DCF Hesaplayıcı", "📈 Çarpan (Comps) Hesaplayıcı"]
)

with tab_report:
    st.subheader("Günlük Roadmap")
    if days_left > 0:
        per_day = max(1, round(len(REPORT_SECTIONS) / days_left, 1))
        st.caption(
            f"{days_left} gün, {len(REPORT_SECTIONS)} bölüm → günde ortalama {per_day} bölüm ilerletmen gerekiyor."
        )
        roadmap_rows = []
        section_idx = 0
        for day_offset in range(days_left):
            day = datetime.date.today() + datetime.timedelta(days=day_offset)
            if section_idx < len(REPORT_SECTIONS):
                target = REPORT_SECTIONS[section_idx]
                section_idx += 1
            else:
                target = "Gözden geçirme / revizyon"
            roadmap_rows.append({"Tarih": day.strftime("%d %b"), "Hedef": target})
        st.table(roadmap_rows)
    st.info(
        "Not: geçmiş yıl birincilerinin raporlarını incelemek istersen (CFA Institute Research Challenge "
        "kazanan raporları) bana linkleri/PDF'leri gönder — genel/uydurma tavsiye vermek yerine gerçek "
        "örnekler üzerinden karşılaştırma yaparım."
    )

    st.subheader("Rapor Bölümleri")
    st.caption("Her bölümü tamamladıkça işaretle. İlerleme bu oturumda tutulur.")

    if "cfa_progress" not in st.session_state:
        st.session_state["cfa_progress"] = {s: False for s in REPORT_SECTIONS}

    for section in REPORT_SECTIONS:
        st.session_state["cfa_progress"][section] = st.checkbox(
            section, value=st.session_state["cfa_progress"][section], key=f"cfa_{section}"
        )

    done = sum(st.session_state["cfa_progress"].values())
    total = len(REPORT_SECTIONS)
    st.progress(done / total)
    st.metric("Tamamlanan bölüm", f"{done}/{total}")

    if client is not None and st.session_state.get("user"):
        if st.button("İlerlemeyi kaydet"):
            try:
                client.table("cfa_progress").upsert(
                    {
                        "user_id": st.session_state["user"].id,
                        "progress": st.session_state["cfa_progress"],
                        "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    }
                ).execute()
                st.success("Kaydedildi.")
            except Exception as exc:
                bug_tracker.log(exc, context="cfa_progress_save")
                st.error("Kaydedilemedi.")

with tab_dcf:
    st.subheader("İndirgenmiş Nakit Akışı (DCF)")
    st.caption("Basit tek-aşamalı DCF: son yıl serbest nakit akışından ileriye projeksiyon + terminal değer.")

    col1, col2 = st.columns(2)
    with col1:
        fcf0 = st.number_input("Son yıl Serbest Nakit Akışı (FCF₀, milyon)", value=100.0, step=1.0)
        growth = st.number_input("Projeksiyon dönemi büyüme oranı (%)", value=8.0, step=0.5) / 100
        years = st.number_input("Projeksiyon süresi (yıl)", min_value=1, max_value=15, value=5)
    with col2:
        wacc = st.number_input("İskonto oranı / WACC (%)", value=12.0, step=0.5) / 100
        terminal_growth = st.number_input("Terminal büyüme oranı (%)", value=3.0, step=0.5) / 100
        shares = st.number_input("Hisse adedi (milyon)", value=100.0, step=1.0)

    if wacc <= terminal_growth:
        st.error("WACC, terminal büyüme oranından büyük olmalı (aksi halde terminal değer sonsuza gider).")
    else:
        pv_sum = 0.0
        fcf = fcf0
        rows = []
        for year in range(1, int(years) + 1):
            fcf = fcf * (1 + growth)
            pv = fcf / ((1 + wacc) ** year)
            pv_sum += pv
            rows.append({"Yıl": year, "FCF": round(fcf, 2), "PV(FCF)": round(pv, 2)})

        terminal_value = (fcf * (1 + terminal_growth)) / (wacc - terminal_growth)
        pv_terminal = terminal_value / ((1 + wacc) ** years)
        enterprise_value = pv_sum + pv_terminal
        value_per_share = enterprise_value / shares if shares > 0 else 0

        st.table(rows)

        c1, c2, c3 = st.columns(3)
        c1.metric("Terminal Değer (bugünkü)", f"{pv_terminal:,.1f} M")
        c2.metric("Firma Değeri (Enterprise Value)", f"{enterprise_value:,.1f} M")
        c3.metric("Hisse Başı Değer", f"{value_per_share:,.2f}")

        st.caption(
            "Bu basitleştirilmiş bir tek-aşamalı DCF — net borç/nakit düzeltmesi, opsiyon dilüsyonu gibi "
            "kalemler dahil değil. Gerçek CFA raporunda bu kalemleri elle ekle."
        )

with tab_comps:
    st.subheader("Çarpan (Comparable Companies) Analizi")
    st.caption("Benzer şirketlerin çarpanlarını gir, hedef şirketin metriğine uygulayıp ima edilen değeri gör.")

    metric_name = st.selectbox("Metrik", ["EV/EBITDA", "P/E", "EV/Sales"])
    target_metric_value = st.number_input(f"Hedef şirketin {metric_name} paydası (EBITDA/Net Kar/Satış, milyon)", value=50.0)

    st.markdown("**Benzer şirket çarpanları**")
    default_peers = [
        {"Şirket": "Peer 1", "Çarpan": 8.0},
        {"Şirket": "Peer 2", "Çarpan": 9.5},
        {"Şirket": "Peer 3", "Çarpan": 7.2},
    ]
    peers = st.data_editor(default_peers, num_rows="dynamic", key="peers_editor")

    multiples = [p["Çarpan"] for p in peers if p.get("Çarpan") not in (None, "")]
    if multiples:
        avg_multiple = sum(multiples) / len(multiples)
        median_multiple = sorted(multiples)[len(multiples) // 2]
        implied_value_avg = target_metric_value * avg_multiple
        implied_value_median = target_metric_value * median_multiple

        c1, c2 = st.columns(2)
        c1.metric(f"Ortalama {metric_name} ile ima edilen değer", f"{implied_value_avg:,.1f} M")
        c2.metric(f"Medyan {metric_name} ile ima edilen değer", f"{implied_value_median:,.1f} M")
    else:
        st.info("En az bir benzer şirket çarpanı gir.")
