import datetime
import json
from pathlib import Path

import pandas as pd
import streamlit as st
import yfinance as yf

from utils.bug_tracker import BugTracker
from utils.supabase_client import get_supabase_client
from utils.theme import inject_theme

TICKER = "BRSAN.IS"
PEERS_PATH = Path(__file__).parent.parent / "data" / "cfa_peers.json"
RATIOS_PATH = Path(__file__).parent.parent / "data" / "ratio_encyclopedia.json"


@st.cache_data(ttl=300)
def get_live_market_data():
    t = yf.Ticker(TICKER)
    fi = t.fast_info
    return {
        "lastPrice": fi.get("lastPrice"),
        "previousClose": fi.get("previousClose"),
        "marketCap": fi.get("marketCap"),
        "shares": fi.get("shares"),
        "yearHigh": fi.get("yearHigh"),
        "yearLow": fi.get("yearLow"),
        "currency": fi.get("currency"),
    }

st.set_page_config(page_title="CFA Research Challenge", page_icon="📊", layout="wide")
inject_theme()

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

TARGET_COMPANY = "Borusan Mannesmann Boru (Borusan Birleşik Boru Fabrikaları San. ve Tic. A.Ş., BIST: BRSAN)"

st.title("📊 CFA Research Challenge")
st.caption(f"Hedef şirket: {TARGET_COMPANY}")

days_left = (DEADLINE - datetime.date.today()).days
if days_left >= 0:
    st.error(f"⏳ Son başvuru tarihine {days_left} gün kaldı — {DEADLINE.strftime('%d %B %Y')}")
else:
    st.warning("Son başvuru tarihi geçti.")

with st.expander("🏭 Şirket Profili (kaynak: Borusan Boru resmi 1Ç26 yatırımcı sunumu)", expanded=True):
    st.markdown(
        """
**Ortaklık yapısı:** Borusan Grubu %83,93 (Borusan Holding %74,85, Borusan Yatırım ve Pazarlama %9,08) —
halka açık kısım %16,07 (Holding'in elindeki halka açık paylarla birlikte fiilen %19,85).
BIST'te 1994'ten beri işlem görüyor.

**Faaliyet:** Çelik boru üreticisi — 10 tesis (Türkiye/Gemlik ana kampüs, ABD/Baytown-Panama City-Mobile,
İtalya/Vobarno, Romanya), 1,7 milyon ton kapasite, 4 segment: Altyapı&Proje, Endüstri&İnşaat, Otomotiv, Enerji.

**1Ç26 finansal özet (konsolide, mln $):**
| | 1Ç26 | 1Ç25 | 2025 (FY) | 2024 (FY) |
|---|---|---|---|---|
| Gelir | 421,6 | 319,1 | 1.796,1 | 1.689,5 |
| FAVÖK (EBITDA) | 26,6 | 17,6 | 133,1 | 101,9 |
| FAVÖK Marjı | %6,3 | %5,5 | %7,4 | %6,0 |
| Net Kar | 6,3 | (7,9) | 31,7 | (5,1) |
| Net Finansal Borç | 160 | 251 | 178 | 280 |

**2026 şirket beklentisi (guidance):** Satış hacmi 1,15–1,25 mln ton, gelir 2,1–2,3 milyar $,
FAVÖK marjı %8–%10.

**Sipariş portföyü:** ABD'de altyapı/enerji segmentinde 2026-2027'ye uzanan ~1,9 milyar $ yeni anlaşma.

*Kaynak: [borusanboru.com yatırımcı sunumu, Ocak-Mart 2026](https://borusanboru.com/Uploads/investor/docs/2026/yatirimci-sunumlari/borusan-boru-yatirimci-sunumu-1c26.pdf) —
2026-09-21'de çekildi. Bu tek kaynak; rapora koymadan önce KAP bildirimleri ve son çeyrek (2Ç26) sunumuyla çapraz doğrula.*
        """
    )
    st.warning(
        "Henüz eklenmedi: detaylı nakit akış tablosu (serbest nakit akımı grafik olarak sunumda var ama "
        "sayısal değeri metinden çıkmadı), WACC hesaplaması. Peer/rakip listesi artık Comps sekmesinde var."
    )

try:
    peers_data_preview = json.loads(PEERS_PATH.read_text(encoding="utf-8"))
except Exception:
    peers_data_preview = {}

if peers_data_preview.get("ownership"):
    own = peers_data_preview["ownership"]
    with st.expander("👥 Ortaklık Yapısı (kaynak: EquityRT Holdings ekranı, 22 Eylül 2026)"):
        bd = own["breakdown"]
        c1, c2, c3 = st.columns(3)
        c1.metric("Kurumsal (Corporations)", f"%{bd['corporations_pct']:.2f}")
        c2.metric("Kurumlar (Institutions)", f"%{bd['institutions_pct']:.2f}")
        c3.metric("Halka Açık & Diğer", f"%{bd['public_and_other_pct']:.2f}")
        st.markdown("**En büyük kurumsal ortaklar:**")
        st.dataframe(own["top_corporations"], use_container_width=True, hide_index=True)
        st.markdown("**En büyük kurumsal yatırımcılar (fonlar):**")
        st.dataframe(own["top_institutions"], use_container_width=True, hide_index=True)
        st.caption(
            "🧠 Okuma: %77,9'u tek elde (Borusan Mannesmann Boru Yatırım Holding) — bu, kontrol gücünün "
            "tamamen ana ortaklıkta olduğu, halka açık kısmın küçük olduğu anlamına gelir (float riski/likidite "
            "CFA raporunda mutlaka değinilmesi gereken bir nokta). Vanguard/BlackRock/Goldman Sachs gibi "
            "küresel isimlerin varlığı, kurumsal yatırımcı ilgisinin uluslararası olduğunu gösterir."
        )

if peers_data_preview.get("recent_news"):
    with st.expander("📰 Son Haberler (kaynak: EquityRT News ekranı — Reuters / Turkish Company News)"):
        for item in peers_data_preview["recent_news"]["items"]:
            st.markdown(f"- **{item['date']}** — {item['headline']} _(​{item['source']})_")
        st.caption(
            "🧠 Okuma: Ağustos 2026'daki art arda ABD sipariş haberleri (~$555M + ~$360M) — Rasyo "
            "Ansiklopedisi'ndeki F/K bölümünde anlatılan 'sipariş portföyü → gelecek kâr → F/K normalleşmesi' "
            "zincirinin tam kanıtı. Raporunda bu haberleri doğrudan valuation gerekçesi olarak kullanabilirsin."
        )

st.subheader(f"📡 Canlı Piyasa Verisi — {TICKER}")
st.caption("Kaynak: Yahoo Finance (yfinance) — yaklaşık 15 dk gecikmeli BIST verisi, önbellek 5 dk.")
try:
    md = get_live_market_data()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Son Fiyat", f"{md['lastPrice']:,.2f} {md['currency']}",
              delta=f"{md['lastPrice'] - md['previousClose']:,.2f}" if md["lastPrice"] and md["previousClose"] else None)
    c2.metric("Piyasa Değeri", f"{md['marketCap'] / 1e9:,.2f} milyar {md['currency']}" if md["marketCap"] else "—")
    c3.metric("Hisse Adedi", f"{md['shares']:,.0f}" if md["shares"] else "—")
    c4.metric("52 Hafta Aralığı", f"{md['yearLow']:,.1f} – {md['yearHigh']:,.1f}" if md["yearLow"] else "—")
except Exception as exc:
    bug_tracker.log(exc, context="cfa_live_market_data")
    st.error("Canlı veri çekilemedi (bağlantı sorunu olabilir).")

with st.expander("📁 EquityRT Excel'ini yükle"):
    st.caption(
        "EquityRT'den export ettiğin Excel dosyasını buraya yükle — sadece bu oturumda görüntülenir, "
        "kaydedilmez. İçeriğe göre hangi sütunları DCF/comps'a bağlayacağımızı birlikte netleştiririz."
    )
    uploaded = st.file_uploader("Excel dosyası (.xlsx)", type=["xlsx"])
    if uploaded is not None:
        try:
            xls = pd.ExcelFile(uploaded)
            sheet = st.selectbox("Sayfa (sheet) seç:", xls.sheet_names)
            df = xls.parse(sheet)
            st.dataframe(df, use_container_width=True)
        except Exception as exc:
            bug_tracker.log(exc, context="cfa_equityrt_upload")
            st.error("Excel okunamadı — dosya formatını kontrol et.")

tab_report, tab_dcf, tab_comps, tab_ratios = st.tabs(
    ["📝 Rapor İlerleme Takibi", "💰 DCF Hesaplayıcı", "📈 Çarpan (Comps) Hesaplayıcı", "📚 Rasyo Ansiklopedisi"]
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
    st.caption(
        "Varsayılan FCF₀ = Borusan Boru'nun 2025 FAVÖK'ü (133,1 mln $) — gerçek Serbest Nakit Akımı değil, "
        "sadece başlangıç noktası. Yatırım harcaması ve işletme sermayesi değişimini düşüp gerçek FCF'yi "
        "nakit akış tablosundan (KAP/faaliyet raporu) çekip buraya elle gir."
    )

    col1, col2 = st.columns(2)
    with col1:
        fcf0 = st.number_input("Son yıl Serbest Nakit Akışı (FCF₀, milyon $)", value=133.1, step=1.0)
        growth = st.number_input(
            "Projeksiyon dönemi büyüme oranı (%)", value=10.0, step=0.5,
            help="Şirket 2026 guidance'ı gelir için %17-28 büyüme, FAVÖK marjı için %8-10 aralığı veriyor — bu tek bir büyüme oranı değil, kendi varsayımını gir."
        ) / 100
        years = st.number_input("Projeksiyon süresi (yıl)", min_value=1, max_value=15, value=5)
    with col2:
        wacc = st.number_input("İskonto oranı / WACC (%)", value=12.0, step=0.5) / 100
        terminal_growth = st.number_input("Terminal büyüme oranı (%)", value=3.0, step=0.5) / 100
        shares = st.number_input(
            "Hisse adedi (milyon)", value=141.77, step=1.0,
            help="Kaynak: Yahoo Finance (yfinance) canlı veri, yukarıdaki 'Canlı Piyasa Verisi' bölümü — 141.771.582 hisse."
        )

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
    st.caption("Kaynak: data/cfa_peers.json — EquityRT'den gönderdiğin veriyle doldurulur, uydurma sayı yok.")

    try:
        peers_data = json.loads(PEERS_PATH.read_text(encoding="utf-8"))
    except Exception as exc:
        bug_tracker.log(exc, context="cfa_peers_load")
        peers_data = {"peers": [], "target": {}}

    if peers_data.get("source"):
        st.caption(f"Birincil kaynak: {peers_data['source']}")
    if peers_data.get("note"):
        st.warning(peers_data["note"])

    target = peers_data.get("target", {})
    peers_list = peers_data.get("peers", [])

    if not peers_list:
        st.info("Henüz hiç peer şirket eklenmedi — `data/cfa_peers.json` boş.")
    else:
        rows = [
            {"Şirket": p["name"], "Ülke": p.get("ulke", "—"), "Piyasa Değeri (mn $)": p["market_cap_mn_usd"],
             "P/BV": p["p_bv"], "P/E": p["p_e"]}
            for p in peers_list
        ]
        if target:
            rows.append({
                "Şirket": f"⭐ {target['name']} (hedef)", "Ülke": "Türkiye",
                "Piyasa Değeri (mn $)": target.get("market_cap_mn_usd"),
                "P/BV": target.get("p_bv"), "P/E": target.get("p_e"),
            })
        st.dataframe(rows, use_container_width=True, hide_index=True)

        pes = [p["p_e"] for p in peers_list if p.get("p_e")]
        pbvs = [p["p_bv"] for p in peers_list if p.get("p_bv")]
        mean_pe = sum(pes) / len(pes) if pes else None
        median_pe = sorted(pes)[len(pes) // 2] if pes else None
        mean_pbv = sum(pbvs) / len(pbvs) if pbvs else None
        median_pbv = sorted(pbvs)[len(pbvs) // 2] if pbvs else None

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Peer ortalama (mean) P/E", f"{mean_pe:.2f}" if mean_pe else "—")
        c2.metric("Peer medyan (median) P/E", f"{median_pe:.2f}" if median_pe else "—")
        c3.metric("Peer ortalama P/BV", f"{mean_pbv:.2f}" if mean_pbv else "—")
        c4.metric("Peer medyan P/BV", f"{median_pbv:.2f}" if median_pbv else "—")

        if target.get("p_e") and median_pe:
            st.metric("BRSAN P/E vs medyan", f"{target['p_e'] - median_pe:+.2f}",
                       help="Pozitifse BRSAN peer medyanına göre daha yüksek çarpanla işlem görüyor.")

        with st.expander("🧠 Mean (ortalama) vs Median (medyan) — hangisini ne zaman kullanmalı?"):
            st.markdown(
                f"""
**Mean (aritmetik ortalama):** Tüm değerleri topla, adede böl. Peer P/E ortalaması: {', '.join(f'{v:.2f}' for v in pes)} → toplam / {len(pes)} = **{mean_pe:.2f}**.

**Median (medyan):** Değerleri küçükten büyüğe sırala, ortadaki değeri al. {len(pes)} şirket olduğu için sıralayınca ortadaki (7. sıradaki) değer **{median_pe:.2f}**.

**🔑 Neden ikisi farklı çıkıyor, hangisine güvenmeli:**
Mean, **aşırı uç (outlier) değerlerden çok etkilenir** — listede Cleveland-Cliffs'in P/E'si yok (veri eksik, ortalamaya hiç girmiyor) ama Ereğli Demir Çelik'in 32,09 gibi yüksek bir P/E'si var, bu tek başına ortalamayı yukarı çeker. Median ise outlier'lara karşı **dayanıklıdır** (robust) — sırf bir şirketin çarpanı aşırı olduğu için değişmez.

**⚠️ Sınav/rapor tuzağı:** Comps analizinde CFA charterholder'lar neredeyse her zaman **medyanı** tercih eder, çünkü peer grupları genelde birkaç aşırı değer (çok küçük/çok büyük şirket, zarar eden şirket, kriz yaşayan şirket) içerir ve mean bunlardan çarpıtılır. Raporunda 'peer ortalaması X' yerine 'peer medyanı X' demek, jüriye istatistik okuryazarlığını gösterir.

**Pratik kural:** Peer grubun küçükse (5-6 şirketten az) veya dağılım çarpıksa (biri aşırı yüksek/düşük) → medyana güven. Peer grubun büyük ve homojense (BRSAN'daki gibi 14 şirket, benzer sektör) → ikisi zaten birbirine yakın çıkar, farkın büyüklüğü senin için bir 'peer grubu ne kadar dağınık' sinyalidir.
                """
            )

        if peers_data.get("sector_median"):
            sm = peers_data["sector_median"]
            st.caption(f"EquityRT'nin kendi sektör medyanı: P/E {sm.get('p_e')}, P/BV {sm.get('p_bv')} — yukarıdaki hesapladığımızla karşılaştır.")

    st.markdown("---")
    st.markdown("**Serbest deneme alanı** — kendi çarpanlarınla implied value hesapla:")
    metric_name = st.selectbox("Metrik", ["P/E", "P/BV"])
    target_metric_value = st.number_input(f"Hedef şirketin {metric_name} paydası (Net Kâr veya Defter Değeri, milyon)", value=50.0)

    field = "p_e" if metric_name == "P/E" else "p_bv"
    default_peers = [{"Şirket": p["name"], "Çarpan": p.get(field)} for p in peers_list] or [{"Şirket": "", "Çarpan": None}]
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

with tab_ratios:
    st.subheader("📚 Rasyo Ansiklopedisi — BRSAN özelinde")
    try:
        ratios_data = json.loads(RATIOS_PATH.read_text(encoding="utf-8"))
    except Exception as exc:
        bug_tracker.log(exc, context="ratio_encyclopedia_load")
        ratios_data = {"source": None, "ratios": []}

    if ratios_data.get("source"):
        st.caption(f"Birincil kaynak: {ratios_data['source']}")

    for r in ratios_data.get("ratios", []):
        with st.expander(f"{r['baslik']} — {r['deger']}"):
            st.markdown(f"**Anlamı:** {r['anlami']}")
            st.markdown(f"**Kim, neden kullanır:** {r['kim_kullanir']}")
            st.markdown(f"**Nasıl kullanılır:** {r['nasil_kullanilir']}")
            c1, c2 = st.columns(2)
            with c1:
                st.markdown(f"**👤 Bireysel yatırımcı okuması:**\n\n{r['bireysel_okuma']}")
            with c2:
                st.markdown(f"**🎓 Deneyimli analist okuması:**\n\n{r['deneyimli_okuma']}")
            st.markdown(f"**⚠️ Gözden kaçırılmaması gerekenler / tuzaklar:** {r['tuzaklar']}")
            st.markdown(f"**📰 Haber ↔ Bilanço ↔ Fiyat bağlantısı:** {r['haber_baglantisi']}")

    if not ratios_data.get("ratios"):
        st.info("Henüz rasyo eklenmedi.")
