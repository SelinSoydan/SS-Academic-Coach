import json
import random
import statistics
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

from utils import valuation as v
from utils.theme import inject_theme

st.set_page_config(page_title="Borusan Equity Cockpit", page_icon="🏆", layout="wide")
inject_theme()

ROOT = Path(__file__).parent.parent
PITCH = json.loads((ROOT / "data" / "brsan_pitch.json").read_text(encoding="utf-8"))
PEERS = json.loads((ROOT / "data" / "cfa_peers.json").read_text(encoding="utf-8"))
SRC = PITCH["sources"]

PINK, PLUM, LAV, ROSE, MAUVE = "#C2578B", "#4A2E45", "#B39DDB", "#E58FB3", "#8E6C8A"


def tr(x: float, d: int = 1) -> str:
    """Türkçe sayı biçimi: binlik nokta, ondalık virgül."""
    s = f"{x:,.{d}f}"
    return s.replace(",", "§").replace(".", ",").replace("§", ".")


def pct(x: float, d: int = 1, sign: bool = False) -> str:
    # Eksi için ASCII "-": st.metric delta rengini baştaki bu karaktere göre seçiyor
    val = x * 100
    prefix = ("+" if val > 0 else "-" if val < 0 else "") if sign else ("-" if val < 0 else "")
    return f"{prefix}%{tr(abs(val), d)}"


def md(s: str) -> str:
    """Markdown metninde $ işaretini kaçırır; iki $ arası yoksa LaTeX formülü gibi render ediliyor."""
    return s.replace("$", "\\$")


def src_link(key: str) -> str:
    s = SRC[key]
    return f"[{s['ad']}]({s['url']})" if s.get("url") else s["ad"]


def html(s: str) -> None:
    st.markdown(s, unsafe_allow_html=True)


def card(pill: str, pill_cls: str, title: str, big: str, body: str, src: str) -> str:
    return (
        f'<div class="sac-card"><span class="sac-pill {pill_cls}">{pill}</span>'
        f'<h4>{title}</h4><div class="sac-big">{big}</div><p>{body}</p>'
        f'<div class="sac-src">Kaynak: {src}</div></div>'
    )


# Çekirdek metrikler: her rakam JSON'daki kaynaklı veriden türetiliyor
FIN = PITCH["financials"]
P = FIN["donemler"]
BASE = FIN["ttm_bazi"]


def ttm_of(key: str) -> float:
    return v.ttm(P[BASE["yil"]][key], P[BASE["onceki"]][key], P[BASE["guncel"]][key])


TTM_REV, TTM_EBITDA, TTM_NI = ttm_of("gelir"), ttm_of("favok"), ttm_of("net_kar")
ND = P[FIN["net_borc_donemi"]]["net_borc"]
MKT = PITCH["market_snapshot"]
MCAP = MKT["market_cap_mn_usd"]
EV = v.enterprise_value(MCAP, ND)

G = PITCH["guidance_2026"]
REV_LO, REV_HI = G["gelir_mn_usd"]
M_LO, M_HI = G["favok_marji"]
REV_MID, M_MID = (REV_LO + REV_HI) / 2, (M_LO + M_HI) / 2
E26_LO, E26_MID, E26_HI = REV_LO * M_LO, REV_MID * M_MID, REV_HI * M_HI

NARROW = PEERS["narrow_peers"]
PEER_TTM = [p["ev_ebitda_ttm"] for p in NARROW]
PEER_FWD = [p["ev_ebitda_forward"] for p in NARROW]
PEER_PE = [p["p_e_ttm"] for p in NARROW]
PEER_PB = [p["p_bv"] for p in NARROW]
PEER_NAMES = " ve ".join(p["name"].replace(" SA", "") for p in NARROW)
SECTOR = PEERS["sector_median"]
LEV = FIN["kaldirac_serisi"]["degerler"]
SEG = PITCH["segmentler_1y26"]
CF = FIN["nakit_akisi_1y26"]
NEW_ORDERS = sum(o["tutar_mn_usd"] for o in PITCH["siparisler"] if o["tarih"].startswith("2026-08"))


@st.cache_data(ttl=300, show_spinner=False)
def live_quote():
    try:
        import yfinance as yf

        fi = yf.Ticker("BRSAN.IS").fast_info
        price, prev = fi.get("lastPrice"), fi.get("previousClose")
        if not price:
            return None
        return {"price": price, "prev": prev, "cur": fi.get("currency") or "TRY"}
    except Exception:
        return None


# HERO
quote = live_quote()
kpis = [
    ("Piyasa değeri", f"{tr(MCAP)} mn $", f"EquityRT, {MKT['tarih']}"),
    ("Firma değeri", f"{tr(EV)} mn $", f"PD + {FIN['net_borc_donemi']} net borç"),
    ("FD/FAVÖK son 12 ay", f"{tr(EV / TTM_EBITDA)}x", BASE["etiket"]),
    ("FD/FAVÖK 2026T", f"{tr(EV / E26_MID)}x", "yükseltilmiş rehberliğin ortası"),
    ("F/K", tr(MKT["p_e"], 2), f"mutabakat: {tr(MCAP / TTM_NI, 2)}"),
    ("Net borç / FAVÖK", f"{tr(ND / TTM_EBITDA, 2)}x", f"sunumda {tr(LEV['2Ç26'])}x · 2Ç25'te {tr(LEV['2Ç25'])}x"),
]
if quote:
    chg = quote["price"] / quote["prev"] - 1 if quote["prev"] else 0
    kpis.append(("Canlı fiyat", f"{tr(quote['price'], 2)} {quote['cur']}", f"{pct(chg, 2, sign=True)} · yfinance, gecikmeli"))
kpi_html = "".join(
    f'<div class="sac-kpi"><div class="l">{l}</div><div class="v">{val}</div><div class="s">{s}</div></div>'
    for l, val, s in kpis
)
html(
    '<div class="sac-hero">'
    '<div class="sac-eyebrow">CFA Institute Research Challenge 2026/27 · Equity Research Cockpit</div>'
    f'<div class="sac-hero-title">Borusan Boru<span>BIST: {PITCH["meta"]["ticker"]}</span></div>'
    f'<div class="sac-hero-sub">{PITCH["meta"]["endustri"]}. {PITCH["meta"]["tesis"]}. '
    f'{PITCH["meta"]["kapasite"]} kapasite, 1Y26 gelirinin %{SEG["abd_gelir_payi"]["1Y26"]}\'i ABD\'den. '
    'Buradaki her rakamın kaynağı belli, her hesabın formülü açık.</div>'
    f'<div class="sac-kpi-grid">{kpi_html}</div></div>'
)

tabs = st.tabs([
    "🎯 Yatırım Tezi",
    "📊 Değerleme Masası",
    "📈 Finansal Analiz",
    "⚠️ Risk Matrisi",
    "🌱 ESG",
    "🏆 CFA Puan Haritası",
    "🎤 Jüri Provası",
])

# 1. YATIRIM TEZİ
with tabs[0]:
    html(
        '<div class="sac-thesis"><b>Tezin sorusu tek cümlede:</b> Piyasa BRSAN\'ı geçmiş kâra göre peer\'larından '
        'belirgin pahalı, yükseltilmiş 2026 rehberliğine göre ise Tenaris\'e yakın fiyatlıyor. Raporun işi, '
        '2Ç26\'daki %11,5 marjın ve sipariş portföyünün kalıcı kârlılığa dönüşüp dönüşmeyeceğini test etmek.</div>'
    )
    g_lo, g_hi = v.growth(REV_LO, P["2025"]["gelir"]), v.growth(REV_HI, P["2025"]["gelir"])
    prev_g = G["onceki"]
    c1, c2, c3 = st.columns(3)
    c1.markdown(card(
        "LEHTE", "green", "Büyüme görünürlüğü", f"{tr(REV_LO / 1000)} ile {tr(REV_HI / 1000)} mlr $",
        f"2026 gelir rehberliği, 2025'e göre {pct(g_lo, 0)} ile {pct(g_hi, 0)} büyüme demek. Rehberlik 2Ç26'da "
        f"yukarı çekildi (önce {tr(prev_g['gelir_mn_usd'][0] / 1000)} ile {tr(prev_g['gelir_mn_usd'][1] / 1000)} mlr $). "
        f"Altyapı ve Proje sipariş portföyü yaklaşık 2,6 mlr $, Ağustos'ta buna yaklaşık {tr(NEW_ORDERS, 0)} mn $ "
        "yeni ABD siparişi eklendi.",
        "2Ç26 sunumu s.3 ve s.23, KAP",
    ), unsafe_allow_html=True)
    c2.markdown(card(
        "LEHTE", "green", "Bilanço onarımı", f"{tr(LEV['2Ç25'])}x → {tr(LEV['2Ç26'])}x",
        f"Net borç/FAVÖK bir yılda {tr(LEV['2Ç25'])}x'ten {tr(LEV['2Ç26'])}x'e indi. Net borç {tr(ND, 0)} mn $, "
        f"kasa {tr(CF['kasa_2c26'], 0)} mn $. 1Y26 serbest nakit akımı {tr(CF['serbest_nakit_akimi'], 0)} mn $, "
        f"ama {tr(CF['isletme_sermayesi'], 0)} mn $'ı işletme sermayesinden geldi.",
        "2Ç26 sunumu s.21 ve s.22",
    ), unsafe_allow_html=True)
    c3.markdown(card(
        "SORGULA", "amber", "Değerleme ve yoğunlaşma", f"{tr(EV / TTM_EBITDA)}x",
        f"Son 12 ay FD/FAVÖK. Aynı çarpan Tenaris'te {tr(PEER_TTM[0])}x, Vallourec'te {tr(PEER_TTM[1])}x. "
        f"Gelirin %{SEG['abd_gelir_payi']['1Y26']}'i tek ülkeden geliyor. Prim ancak marj kalıcı olursa hak ediliyor.",
        "EquityRT 22.09.2026, 2Ç26 sunumu",
    ), unsafe_allow_html=True)

    st.markdown("#### Farkımız nerede olmalı? FaVeS çerçevesi")
    st.caption(
        "Valentine'ın CFA Institute'un RC kaynakları arasında yer alan kitabına göre konsensüs dışı bir görüş, "
        "tahminde, değerlemede ya da piyasa duygusunda somut bir üstünlüğe dayanmalı. Aşağıdakiler bizim önerdiğimiz çalışma hatları."
    )
    fc = st.columns(3)
    for col, f in zip(fc, PITCH["cfa_playbook"]["faves"]):
        col.markdown(card("EDGE", "", f["harf"], "", f["fikir"], src_link("valentine")), unsafe_allow_html=True)

    st.markdown("#### Katalizör takvimi")
    items = "".join(
        f'<div class="sac-tl-item {"future" if c["tur"] == "gelecek" else ""}">'
        f'<div class="sac-tl-date">{c["tarih"]}</div><div>{c["olay"]}</div>'
        f'<div class="sac-src">{c["kaynak"]}</div></div>'
        for c in PITCH["catalysts"]
    )
    html(f'<div class="sac-tl">{items}</div>')
    st.caption(PITCH["siparis_notu"])

    st.markdown("#### Fiyatı ne hareket ettirir? Yukarı ve aşağı katalizörler")
    KY = PITCH["katalizor_yonu"]
    st.caption(KY["not"])
    cu, cdn = st.columns(2)
    for col, items_k, cls, label in ((cu, KY["yukari"], "green", "▲ YUKARI"), (cdn, KY["asagi"], "amber", "▼ AŞAĞI")):
        with col:
            for k in items_k:
                html(
                    f'<div class="sac-card"><span class="sac-pill {cls}">{label}</span>'
                    f'<h4 style="font-size:1.12rem">{k["olay"]}</h4><p>{k["izle"]}</p></div>'
                )

# 2. DEĞERLEME MASASI
with tabs[1]:
    st.markdown("#### Football field: çarpanlar bugünkü fiyat hakkında ne söylüyor?")
    st.caption(md(
        f"Dar peer grubu: {PEER_NAMES} (EquityRT, 22.09.2026). Firma değeri çarpanlarında özsermaye = çarpan x FAVÖK "
        f"eksi {tr(ND, 0)} mn $ net borç. F/K ve PD/DD'de özsermaye = piyasa değeri x (peer çarpanı / BRSAN çarpanı)."
    ))
    ff_rows = [
        ("FD/FAVÖK son 12 ay, dar peer", min(PEER_TTM) * TTM_EBITDA - ND, max(PEER_TTM) * TTM_EBITDA - ND, "Firma değeri çarpanı"),
        ("FD/FAVÖK 2026T, dar peer x rehberlik", min(PEER_FWD) * E26_LO - ND, max(PEER_FWD) * E26_HI - ND, "Firma değeri çarpanı"),
        ("F/K son 12 ay, dar peer", v.equity_from_relative_multiple(MCAP, MKT["p_e"], min(PEER_PE)),
         v.equity_from_relative_multiple(MCAP, MKT["p_e"], max(PEER_PE)), "Özsermaye çarpanı"),
        ("PD/DD, dar peer", v.equity_from_relative_multiple(MCAP, MKT["p_bv"], min(PEER_PB)),
         v.equity_from_relative_multiple(MCAP, MKT["p_bv"], max(PEER_PB)), "Özsermaye çarpanı"),
        ("F/K, geniş sektör medyanı", v.equity_from_relative_multiple(MCAP, MKT["p_e"], SECTOR["p_e"]),
         v.equity_from_relative_multiple(MCAP, MKT["p_e"], SECTOR["p_e"]), "Geniş sektör (bağlam)"),
        ("PD/DD, geniş sektör medyanı", v.equity_from_relative_multiple(MCAP, MKT["p_bv"], SECTOR["p_bv"]),
         v.equity_from_relative_multiple(MCAP, MKT["p_bv"], SECTOR["p_bv"]), "Geniş sektör (bağlam)"),
    ]
    ff = pd.DataFrame([
        {"yontem": r[0], "low": r[1], "high": r[2], "grup": r[3],
         "etiket": tr(r[1], 0) if abs(r[2] - r[1]) < 1 else f"{tr(r[1], 0)} ile {tr(r[2], 0)}"}
        for r in ff_rows
    ])
    color = alt.Color("grup:N", scale=alt.Scale(range=[PINK, LAV, MAUVE]), legend=alt.Legend(orient="bottom", title=None))
    base = alt.Chart(ff).encode(y=alt.Y("yontem:N", sort=None, title=None, axis=alt.Axis(labelLimit=280)))
    x_dom = [min(ff["low"].min(), MCAP) * 0.8, max(ff["high"].max(), MCAP) * 1.22]
    bars = base.mark_bar(size=22, cornerRadius=6).encode(
        x=alt.X("low:Q", title="Özsermaye değeri (mn $)", scale=alt.Scale(domain=x_dom, nice=False),
                axis=alt.Axis(labelExpr="replace(datum.label, ',', '.')")), x2="high:Q", color=color,
        tooltip=[alt.Tooltip("yontem:N", title="Yöntem"), alt.Tooltip("etiket:N", title="Aralık (mn $)")],
    )
    points = base.mark_point(filled=True, size=160, shape="diamond").encode(x="low:Q", color=color).transform_filter(
        "abs(datum.high - datum.low) < 1"
    )
    labels = base.mark_text(align="left", dx=8, color=PLUM, fontSize=11).encode(x="high:Q", text="etiket:N")
    rule_df = pd.DataFrame({"x": [MCAP], "t": [f"Bugünkü piyasa değeri {tr(MCAP, 0)}"]})
    rule = alt.Chart(rule_df).mark_rule(color=PLUM, strokeDash=[6, 4], size=2).encode(x="x:Q")
    rule_txt = alt.Chart(rule_df).mark_text(align="right", dx=-6, dy=8, color=PLUM, fontWeight="bold").encode(
        x="x:Q", y=alt.value(0), text="t:N"
    )
    st.altair_chart((bars + points + labels + rule + rule_txt).properties(height=320), width="stretch")
    st.info(
        f"**Okuma:** Geriye dönük her çarpanda bugünkü piyasa değeri peer aralığının üstünde kalıyor. Sadece ileriye dönük "
        f"FD/FAVÖK satırında, rehberliğin üst ucu ve {NARROW[0]['name'].replace(' SA', '')}'in çarpanı birleşince aralık bugünkü "
        "fiyata uzanıyor. Yani piyasa bugünden iyimser senaryoyu fiyatlıyor. Bu bir tavsiye değil; raporun cevaplaması gereken "
        "sorunun görsel hali. Dar grubun şimdilik iki şirket olduğunu da unutma, aralık Jindal SAW gibi isimlerle güncellenecek."
    )

    st.markdown("#### Duyarlılık: çarpan x 2026 FAVÖK, bugünkü fiyata göre fark")
    ebitda_grid = [E26_LO + (E26_HI - E26_LO) * i / 4 for i in range(5)]
    mult_grid = [5, 6, 7, 8, 9, 10, 11, 12]
    cells = []
    for m in mult_grid:
        for e in ebitda_grid:
            up = v.upside(v.equity_from_ev_multiple(m, e, ND), MCAP)
            cells.append({"carpan": f"{m}x", "m": m, "favok": f"{tr(e, 0)}", "e": e, "up": up * 100, "lbl": pct(up, 0, sign=True)})
    hm = pd.DataFrame(cells)
    heat = alt.Chart(hm).mark_rect(cornerRadius=4).encode(
        x=alt.X("favok:O", title="2026T FAVÖK (mn $), rehberlik aralığı", sort=[f"{tr(e, 0)}" for e in ebitda_grid]),
        y=alt.Y("carpan:O", title="FD/FAVÖK çarpanı", sort=[f"{m}x" for m in reversed(mult_grid)]),
        color=alt.Color("up:Q", scale=alt.Scale(domain=[-60, 0, 60], range=["#D9546A", "#FFF6FA", "#3E9A72"], clamp=True, interpolate="rgb"), legend=None),
        tooltip=[alt.Tooltip("carpan:N", title="Çarpan"), alt.Tooltip("favok:N", title="FAVÖK"), alt.Tooltip("lbl:N", title="Fark")],
    )
    heat_txt = alt.Chart(hm).mark_text(fontSize=12, fontWeight="bold", color=PLUM).encode(
        x=alt.X("favok:O", sort=[f"{tr(e, 0)}" for e in ebitda_grid]),
        y=alt.Y("carpan:O", sort=[f"{m}x" for m in reversed(mult_grid)]), text="lbl:N",
    )
    st.altair_chart((heat + heat_txt).properties(height=330), width="stretch")
    st.caption(
        f"Bugünkü fiyatın ima ettiği 2026T FD/FAVÖK: rehberliğin alt ucunda {tr(EV / E26_LO)}x, ortasında "
        f"{tr(EV / E26_MID)}x, üst ucunda {tr(EV / E26_HI)}x. Karşılaştırma: {NARROW[0]['name']} {tr(PEER_FWD[0])}x, "
        f"{NARROW[1]['name']} {tr(PEER_FWD[1])}x (ileriye dönük, EquityRT)."
    )

    st.markdown("#### Makro şok simülatörü: çelik fiyatı, kur ve hacim FAVÖK'ü nasıl etkiler?")
    st.caption(md(
        f"Baz: 2026 rehberliğinin ortası, gelir {tr(REV_MID, 0)} mn $ ve FAVÖK {tr(E26_MID, 0)} mn $. Değer etkisi bugünkü fiyatın "
        f"ima ettiği {tr(EV / E26_MID)}x çarpanla hesaplanıyor. Maliyet yapısı girdileri şirket verisi değil varsayım; "
        "faaliyet raporundaki maliyet kırılımıyla güncellenmeli."
    ))
    a1, a2, a3, a4 = st.columns(4)
    steel_share = a1.number_input("Girdi çeliğin gelire oranı (%)", 20.0, 90.0, 60.0, step=5.0, help="Varsayım")
    pass_thru = a2.number_input("Fiyat geçişkenliği (%)", 0.0, 100.0, 70.0, step=5.0,
                                help="Çelik maliyet değişiminin ne kadarı satış fiyatına yansıyor. Varsayım.")
    tl_share = a3.number_input("TL cinsi maliyetlerin gelire oranı (%)", 0.0, 50.0, 15.0, step=1.0, help="Varsayım")
    contrib = a4.number_input("Hacimde katkı marjı (%)", 0.0, 50.0, 20.0, step=1.0,
                              help="Ek bir ton satışın FAVÖK'e kattığı pay. Varsayım.")
    b1, b2, b3 = st.columns(3)
    steel_chg = b1.slider("Çelik fiyatı değişimi (%)", -30, 30, -10)
    fx_chg = b2.slider("TL reel değerlenmesi (%)", -20, 20, 10,
                       help="Artı değer: TL, enflasyon farkına göre dolar karşısında reel değer kazanıyor, yani kur makası açılıyor; TL maliyetler dolar bazında şişer.")
    vol_chg = b3.slider("Satış hacmi değişimi (%)", -20, 20, 0)
    IMPLIED_MULT = EV / E26_MID

    def shock(steel: float, fx: float, vol: float) -> tuple:
        d_steel = -REV_MID * steel_share / 100 * steel / 100 * (1 - pass_thru / 100)
        d_fx = -REV_MID * tl_share / 100 * fx / 100
        d_vol = REV_MID * vol / 100 * contrib / 100
        return d_steel, d_fx, d_vol

    ds, dfx, dv = shock(steel_chg, fx_chg, vol_chg)
    new_e = E26_MID + ds + dfx + dv
    new_rev = REV_MID * (1 + vol_chg / 100) + REV_MID * steel_share / 100 * steel_chg / 100 * pass_thru / 100
    s1, s2, s3, s4 = st.columns(4)
    s1.metric("Yeni 2026T FAVÖK", f"{tr(new_e)} mn $", delta=f"{tr(new_e - E26_MID)} mn $")
    s2.metric("Yeni FAVÖK marjı", pct(new_e / new_rev), delta=f"{tr((new_e / new_rev - M_MID) * 100)} puan")
    s3.metric("Özsermaye değerine etkisi", f"{tr((new_e - E26_MID) * IMPLIED_MULT, 0)} mn $",
              delta=pct((new_e - E26_MID) * IMPLIED_MULT / MCAP, 1, sign=True))
    s4.metric("Etki kırılımı (çelik / kur / hacim)", f"{tr(ds, 0)} / {tr(dfx, 0)} / {tr(dv, 0)}")

    tor = []
    for name, lo_d, hi_d in [
        ("Çelik fiyatı ±%10", sum(shock(10, 0, 0)), sum(shock(-10, 0, 0))),
        ("TL reel kur ±%10", sum(shock(0, 10, 0)), sum(shock(0, -10, 0))),
        ("Satış hacmi ±%10", sum(shock(0, 0, -10)), sum(shock(0, 0, 10))),
        ("FAVÖK marjı ±1 puan", -REV_MID * 0.01, REV_MID * 0.01),
    ]:
        tor.append({"surucu": name, "x": 0, "x2": lo_d * IMPLIED_MULT, "yon": "Olumsuz"})
        tor.append({"surucu": name, "x": 0, "x2": hi_d * IMPLIED_MULT, "yon": "Olumlu"})
    tor.append({"surucu": "FD/FAVÖK çarpanı ±1x", "x": 0, "x2": -E26_MID, "yon": "Olumsuz"})
    tor.append({"surucu": "FD/FAVÖK çarpanı ±1x", "x": 0, "x2": E26_MID, "yon": "Olumlu"})
    tdf = pd.DataFrame(tor)
    tdf["lbl"] = tdf["x2"].map(lambda z: f"{'+' if z > 0 else ''}{tr(z, 0)}")
    order = tdf.assign(a=tdf["x2"].abs()).groupby("surucu")["a"].max().sort_values(ascending=False).index.tolist()
    tbars = alt.Chart(tdf).mark_bar(size=22, cornerRadius=4).encode(
        y=alt.Y("surucu:N", sort=order, title=None, axis=alt.Axis(labelLimit=220)),
        x=alt.X("x:Q", title="Özsermaye değerine etkisi (mn $)", axis=alt.Axis(labelExpr="replace(datum.label, ',', '.')")),
        x2="x2:Q",
        color=alt.Color("yon:N", scale=alt.Scale(domain=["Olumsuz", "Olumlu"], range=["#D9546A", "#3E9A72"]), legend=alt.Legend(orient="bottom", title=None)),
        tooltip=["surucu:N", "lbl:N"],
    )
    tt_base = alt.Chart(tdf).encode(y=alt.Y("surucu:N", sort=order), x="x2:Q", text="lbl:N")
    ttxt = (tt_base.mark_text(fontSize=11, color=PLUM, align="left", dx=4).transform_filter("datum.x2 > 0")
            + tt_base.mark_text(fontSize=11, color=PLUM, align="right", dx=-4).transform_filter("datum.x2 <= 0"))
    st.altair_chart((tbars + ttxt).properties(height=250, title="Tornado: her sürücü tek başına oynatılınca değer ne kadar değişir?"), width="stretch")
    st.caption("Tornado, jürinin resmi soru havuzundaki 'değerlemenizi en çok hangi duyarlılık değiştirir?' sorusunun görsel cevabı.")

    st.markdown("#### Senaryolar: ayı, baz, boğa")
    st.caption("Varsayılanlar rehberliğin uçları ve dar peer grubunun ileriye dönük çarpanlarıdır. Hücreleri değiştirip kendi senaryonu savunabilirsin.")
    scen_default = pd.DataFrame([
        {"Senaryo": "Ayı", "Gelir (mn $)": float(REV_LO), "FAVÖK marjı (%)": M_LO * 100, "FD/FAVÖK (x)": min(PEER_FWD)},
        {"Senaryo": "Baz", "Gelir (mn $)": float(REV_MID), "FAVÖK marjı (%)": M_MID * 100, "FD/FAVÖK (x)": round(statistics.mean(PEER_FWD), 2)},
        {"Senaryo": "Boğa", "Gelir (mn $)": float(REV_HI), "FAVÖK marjı (%)": M_HI * 100, "FD/FAVÖK (x)": max(PEER_FWD)},
    ])
    scen = st.data_editor(scen_default, hide_index=True, disabled=["Senaryo"], key="scenario_editor", width="stretch")
    scen_out = []
    for _, r in scen.iterrows():
        e = v.guidance_ebitda(r["Gelir (mn $)"], r["FAVÖK marjı (%)"] / 100)
        eq = v.equity_from_ev_multiple(r["FD/FAVÖK (x)"], e, ND)
        scen_out.append({"Senaryo": r["Senaryo"], "FAVÖK (mn $)": tr(e), "Özsermaye (mn $)": tr(eq, 0),
                         "Bugünkü fiyata göre": pct(v.upside(eq, MCAP), 1, sign=True)})
    st.dataframe(pd.DataFrame(scen_out), hide_index=True)

    st.markdown("#### Monte Carlo: 10.000 senaryoda özsermaye değeri dağılımı")
    mc1, mc2, mc3 = st.columns(3)
    rev_rng = mc1.slider("2026 gelir aralığı (mn $)", 1800, 2800, (int(REV_LO), int(REV_HI)), step=50)
    mar_rng = mc2.slider("FAVÖK marjı aralığı (%)", 5.0, 14.0, (M_LO * 100, M_HI * 100), step=0.5)
    mul_rng = mc3.slider("FD/FAVÖK çarpan aralığı (x)", 3.0, 16.0, (float(min(PEER_FWD)), float(max(PEER_FWD))), step=0.01)

    @st.cache_data(show_spinner=False)
    def monte_carlo(rev_r, mar_r, mul_r, nd, n=10000, seed=42):
        rng = random.Random(seed)
        return sorted(
            v.equity_from_ev_multiple(rng.uniform(*mul_r), rng.uniform(*rev_r) * rng.uniform(*mar_r) / 100, nd)
            for _ in range(n)
        )

    sims = monte_carlo(tuple(rev_rng), tuple(mar_rng), tuple(mul_rng), ND)
    n = len(sims)
    p5, p50, p95 = sims[int(0.05 * n)], sims[int(0.5 * n)], sims[int(0.95 * n)]
    prob_above = sum(1 for s in sims if s > MCAP) / n
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("5. persentil", f"{tr(p5, 0)} mn $")
    m2.metric("Medyan", f"{tr(p50, 0)} mn $", delta=pct(v.upside(p50, MCAP), 1, sign=True))
    m3.metric("95. persentil", f"{tr(p95, 0)} mn $")
    m4.metric("Bugünkü fiyatın üstünde kalma olasılığı", pct(prob_above, 1))
    lo_v, hi_v = sims[0], sims[-1]
    width_b = (hi_v - lo_v) / 40 or 1
    counts = [0] * 40
    for s in sims:
        counts[min(int((s - lo_v) / width_b), 39)] += 1
    hist = pd.DataFrame({"x": [lo_v + width_b * (i + 0.5) for i in range(40)], "adet": counts})
    hist_chart = alt.Chart(hist).mark_bar(color=ROSE, cornerRadiusTopLeft=3, cornerRadiusTopRight=3).encode(
        x=alt.X("x:Q", title="Özsermaye değeri (mn $)", bin=False), y=alt.Y("adet:Q", title="Senaryo sayısı")
    )
    mc_rules = alt.Chart(pd.DataFrame({"x": [MCAP, p50], "c": ["Bugünkü piyasa değeri", "Medyan senaryo"]})).mark_rule(
        size=2, strokeDash=[6, 4]
    ).encode(x="x:Q", color=alt.Color("c:N", scale=alt.Scale(range=[PLUM, PINK]), legend=alt.Legend(orient="bottom", title=None)))
    st.altair_chart((hist_chart + mc_rules).properties(height=260), width="stretch")
    st.caption(
        "Her değişken kendi aralığında eşit olasılıkla çekiliyor; sabit tohum (42) sayesinde sonuç her açılışta aynı ve "
        "tekrarlanabilir. Aralıklar veri değil varsayım: varsayılanlar şirket rehberliği ve dar peer çarpanları."
    )

    st.markdown("#### Reverse DCF: bugünkü fiyat hangi nakit akışını fiyatlıyor?")
    r1, r2 = st.columns(2)
    wacc = r1.slider("WACC, USD bazında (%)", 7.0, 15.0, 11.0, step=0.25, help="Varsayım, veri değil. Kendi WACC hesabınla değiştir.")
    g_term = r2.slider("Sonsuz büyüme (%)", 0.0, 4.0, 2.5, step=0.25, help="Varsayım, veri değil.")
    fcff = v.implied_steady_fcff(EV, wacc / 100, g_term / 100)
    k1, k2, k3 = st.columns(3)
    k1.metric("Piyasanın ima ettiği kalıcı serbest nakit akımı", f"{tr(fcff)} mn $/yıl")
    k2.metric("Son 12 ay FAVÖK'e oranı", pct(fcff / TTM_EBITDA, 0))
    k3.metric("2026T FAVÖK ortasına oranı", pct(fcff / E26_MID, 0))
    st.info(md(
        f"**Okuma:** WACC %{tr(wacc, 2)} ve büyüme %{tr(g_term, 2)} ile piyasa, her yıl yaklaşık {tr(fcff, 0)} mn $ serbest "
        f"nakit akımının sonsuza kadar süreceğini fiyatlıyor. Bu, rehberliğin ortasındaki FAVÖK'ün {pct(fcff / E26_MID, 0)}'i. "
        f"Kıyas için 1Y26 serbest nakit akımı {tr(CF['serbest_nakit_akimi'], 0)} mn $ idi, ama {tr(CF['isletme_sermayesi'], 0)} "
        "mn $'ı işletme sermayesinden geldi. Yatırım yoğun bir işte bu dönüşüm oranı makul mü? Jüriye bu soruyla gitmek güçlü bir hamle."
    ))
    rcells = []
    for w in [8, 9, 10, 11, 12, 13, 14]:
        for gg in [1.0, 1.5, 2.0, 2.5, 3.0, 3.5]:
            f = v.implied_steady_fcff(EV, w / 100, gg / 100)
            rcells.append({"wacc": f"%{w}", "g": f"%{tr(gg)}", "oran": f / E26_MID * 100, "lbl": pct(f / E26_MID, 0)})
    rhm = pd.DataFrame(rcells)
    rheat = alt.Chart(rhm).mark_rect(cornerRadius=4).encode(
        x=alt.X("g:O", title="Sonsuz büyüme", sort=[f"%{tr(x)}" for x in [1.0, 1.5, 2.0, 2.5, 3.0, 3.5]]),
        y=alt.Y("wacc:O", title="WACC", sort=[f"%{w}" for w in [8, 9, 10, 11, 12, 13, 14]]),
        color=alt.Color("oran:Q", scale=alt.Scale(range=["#F6E4F2", "#7B3F6E"], interpolate="rgb"), legend=None),
    )
    rtxt = alt.Chart(rhm).mark_text(fontSize=12, fontWeight="bold").encode(
        x=alt.X("g:O", sort=[f"%{tr(x)}" for x in [1.0, 1.5, 2.0, 2.5, 3.0, 3.5]]),
        y=alt.Y("wacc:O", sort=[f"%{w}" for w in [8, 9, 10, 11, 12, 13, 14]]), text="lbl:N",
        color=alt.condition("datum.oran > 70", alt.value("white"), alt.value(PLUM)),
    )
    st.altair_chart((rheat + rtxt).properties(height=300, title="Gereken nakit dönüşümü: ima edilen serbest nakit akımı / 2026T FAVÖK"), width="stretch")

# 3. FİNANSAL ANALİZ
with tabs[2]:
    h1, h2 = P["1Y25"], P["1Y26"]
    f1, f2, f3, f4 = st.columns(4)
    f1.metric("1Y26 gelir", f"{tr(h2['gelir'])} mn $", delta=pct(v.growth(h2["gelir"], h1["gelir"]), 1, sign=True))
    f2.metric("1Y26 FAVÖK", f"{tr(h2['favok'])} mn $", delta=pct(v.growth(h2["favok"], h1["favok"]), 1, sign=True))
    f3.metric("1Y26 FAVÖK marjı", pct(h2["favok"] / h2["gelir"]),
              delta=f"{tr((h2['favok'] / h2['gelir'] - h1['favok'] / h1['gelir']) * 100)} puan")
    f4.metric("1Y26 net kâr", f"{tr(h2['net_kar'])} mn $", delta=pct(v.growth(h2["net_kar"], h1["net_kar"]), 0, sign=True))

    q_keys = [k for k, d in P.items() if d["tur"] == "ceyrek"]
    qdf = pd.DataFrame([{"donem": k, "gelir": P[k]["gelir"], "marj": P[k]["favok"] / P[k]["gelir"] * 100} for k in q_keys])
    qbase = alt.Chart(qdf).encode(x=alt.X("donem:N", sort=q_keys, title=None))
    qbars = qbase.mark_bar(color=LAV, size=46, cornerRadiusTopLeft=6, cornerRadiusTopRight=6).encode(
        y=alt.Y("gelir:Q", title="Gelir (mn $)")
    )
    qline = qbase.mark_line(color=PINK, strokeWidth=3, point=alt.OverlayMarkDef(size=90, color=PINK)).encode(
        y=alt.Y("marj:Q", title="FAVÖK marjı (%)", scale=alt.Scale(domain=[0, 14]))
    )
    qtxt = qbase.mark_text(dy=-14, color=PINK, fontWeight="bold").encode(
        y=alt.Y("marj:Q", scale=alt.Scale(domain=[0, 14]), axis=None), text=alt.Text("marj:Q", format=".1f")
    )
    cA, cB = st.columns(2)
    with cA:
        st.markdown("##### Çeyreklik gelir ve FAVÖK marjı")
        st.altair_chart(alt.layer(qbars, qline + qtxt).resolve_scale(y="independent").properties(height=280), width="stretch")
    with cB:
        st.markdown("##### Kaldıraç: net borç / son 12 ay FAVÖK")
        ldf = pd.DataFrame([{"donem": k, "x": val} for k, val in LEV.items()])
        lbar = alt.Chart(ldf).mark_bar(color=PINK, size=46, cornerRadiusTopLeft=6, cornerRadiusTopRight=6).encode(
            x=alt.X("donem:N", sort=list(LEV.keys()), title=None), y=alt.Y("x:Q", title="Net borç / FAVÖK (x)")
        )
        ltxt = lbar.mark_text(dy=-10, color=PLUM, fontWeight="bold").encode(text=alt.Text("x:Q", format=".1f"))
        st.altair_chart((lbar + ltxt).properties(height=280), width="stretch")
        st.caption(f"Kaynak: {FIN['kaldirac_serisi']['kaynak']}")

    cC, cD = st.columns(2)
    with cC:
        st.markdown("##### Yıllık gelir ve 2026 rehberliği")
        adf = pd.DataFrame([
            {"donem": "2024", "gelir": P["2024"]["gelir"], "lo": None, "hi": None},
            {"donem": "2025", "gelir": P["2025"]["gelir"], "lo": None, "hi": None},
            {"donem": "Son 12 ay", "gelir": TTM_REV, "lo": None, "hi": None},
            {"donem": "2026T", "gelir": REV_MID, "lo": REV_LO, "hi": REV_HI},
        ])
        abars = alt.Chart(adf).mark_bar(size=46, cornerRadiusTopLeft=6, cornerRadiusTopRight=6).encode(
            x=alt.X("donem:N", sort=list(adf["donem"]), title=None), y=alt.Y("gelir:Q", title="Gelir (mn $)"),
            color=alt.condition("datum.donem == '2026T'", alt.value(ROSE), alt.value(LAV)),
        )
        aerr = alt.Chart(adf.dropna()).mark_rule(color=PLUM, size=3).encode(x=alt.X("donem:N", sort=list(adf["donem"])), y="lo:Q", y2="hi:Q")
        st.altair_chart((abars + aerr).properties(height=260), width="stretch")
    with cD:
        st.markdown("##### 1Y26 segment dağılımı ve yıllık değişim")
        sdf = pd.DataFrame(SEG["items"])
        sdf["lbl"] = sdf.apply(lambda r: f"%{r['pay']} pay · {pct(r['yillik_degisim'] / 100, 1, sign=True)}", axis=1)
        sbar = alt.Chart(sdf).mark_bar(size=26, cornerRadiusEnd=6).encode(
            y=alt.Y("segment:N", sort="-x", title=None), x=alt.X("gelir:Q", title="Gelir (mn $)"),
            color=alt.condition("datum.yillik_degisim > 0", alt.value(PINK), alt.value("#C9B6C4")),
        )
        stxt = sbar.mark_text(align="left", dx=6, color=PLUM, fontSize=11).encode(text="lbl:N")
        st.altair_chart((sbar + stxt).properties(height=260), width="stretch")
        st.caption(f"Kaynak: {SEG['kaynak']}")

    op_lev_25 = v.growth(P["2025"]["favok"], P["2024"]["favok"]) / v.growth(P["2025"]["gelir"], P["2024"]["gelir"])
    st.markdown("#### Analist notları")
    st.markdown(
        f"- **Faaliyet kaldıracı çalışıyor.** 2025'te gelir {pct(v.growth(P['2025']['gelir'], P['2024']['gelir']))} artarken "
        f"FAVÖK {pct(v.growth(P['2025']['favok'], P['2024']['favok']))} arttı; FAVÖK gelirden yaklaşık {tr(op_lev_25)} kat hızlı büyüdü.\n"
        f"- **Büyümenin motoru tek segment.** Altyapı ve Proje 1Y26'da {pct(SEG['items'][0]['yillik_degisim'] / 100, 1, sign=True)} "
        f"büyüyüp gelirin %{SEG['items'][0]['pay']}'ine ulaştı; Endüstri ve İnşaat ise {pct(SEG['items'][2]['yillik_degisim'] / 100, 1, sign=True)} geriledi.\n"
        f"- **Marj oynak.** Çeyreklik FAVÖK marjı 1Ç26'da %{tr(P['1Ç26']['favok'] / P['1Ç26']['gelir'] * 100)}, 2Ç26'da "
        f"%{tr(P['2Ç26']['favok'] / P['2Ç26']['gelir'] * 100)}. Hangisinin normal olduğu tezin ta kendisi.\n"
        f"- **Mutabakat.** Piyasa değeri / son 12 ay net kâr = {tr(MCAP, 1)} / {tr(TTM_NI, 1)} = {tr(MCAP / TTM_NI, 2)}; "
        f"EquityRT Peer Performance ekranındaki {tr(MKT['p_e'], 2)} ile tutuyor. Snapshot ekranındaki {tr(MKT['p_e_snapshot_ekrani'], 2)} farklı bir dönem ya da kur bazı kullanıyor olmalı."
    )
    st.markdown("#### Rasyo panosu: BRSAN ve dar peer grubu")
    BV = MCAP / MKT["p_bv"]
    TA = PEERS["target"]["total_assets_mn_usd"]
    tn, vk = NARROW[0], NARROW[1]

    def xf(val, d=1):
        return "yok" if val is None else f"{tr(val, d)}x"

    def pf(val, d=1):
        return "yok" if val is None else f"%{tr(val, d)}"

    capex_rev = -CF["yatirim"] / h2["gelir"]
    ratio_rows = [
        ("Değerleme", "FD/FAVÖK son 12 ay", xf(EV / TTM_EBITDA), xf(tn["ev_ebitda_ttm"]), xf(vk["ev_ebitda_ttm"]), "FD / son 12 ay FAVÖK"),
        ("Değerleme", "FD/FAVÖK ileriye dönük", xf(EV / E26_MID), xf(tn["ev_ebitda_forward"]), xf(vk["ev_ebitda_forward"]),
         "BRSAN: rehberlik ortası; peer'lar: EquityRT konsensüsü"),
        ("Değerleme", "F/K son 12 ay", xf(MKT["p_e"], 2), xf(tn["p_e_ttm"], 2), xf(vk["p_e_ttm"], 2), "EquityRT; USD son 12 ay net kârla mutabık"),
        ("Değerleme", "PD/DD", xf(MKT["p_bv"], 2), xf(tn["p_bv"], 2), xf(vk["p_bv"], 2), "EquityRT"),
        ("Değerleme", "FD/Satış son 12 ay", xf(EV / TTM_REV, 2), "yok", "yok", "FD / son 12 ay gelir"),
        ("Kârlılık", "FAVÖK marjı son 12 ay", pct(TTM_EBITDA / TTM_REV), "yok", "yok", "Son 12 ay FAVÖK / gelir"),
        ("Kârlılık", "Net kâr marjı son 12 ay", pct(TTM_NI / TTM_REV), "yok", "yok", "Son 12 ay net kâr / gelir"),
        ("Kârlılık", "ROE", pct(TTM_NI / BV), pf(tn["roe_pct"]), pf(vk["roe_pct"]), "Net kâr / özsermaye (PD ÷ PD/DD)"),
        ("Kârlılık", "ROA", pct(TTM_NI / TA), pf(tn["roa_pct"]), pf(vk["roa_pct"]), "Net kâr / toplam aktif (EquityRT)"),
        ("Verimlilik", "Aktif devir hızı", xf(TTM_REV / TA, 2), "yok", "yok", "Son 12 ay gelir / toplam aktif"),
        ("Bilanço", "Net borç / FAVÖK", xf(ND / TTM_EBITDA, 2), xf(tn["net_debt_ebitda"], 2), xf(vk["net_debt_ebitda"], 2), "Eksi değer net nakit demek"),
        ("Bilanço", "Borç / aktif", "yok", pf(tn["debt_asset_pct"]), pf(vk["debt_asset_pct"]), "EquityRT; BRSAN için brüt borç KAP'tan eklenecek"),
        ("Nakit", "Yatırım harcaması / gelir 1Y26", pct(capex_rev), "yok", "yok", "2Ç26 sunumu s.22"),
        ("Nakit", "Nakit dönüşümü 1Y26", pct(CF["serbest_nakit_akimi"] / h2["favok"], 0), "yok", "yok", "SNA / FAVÖK, işletme sermayesi dahil"),
        ("Ortaklara", "Temettü verimi", "yok (2025 kârı dağıtılmadı)", pf(tn["dividend_yield_ttm_pct"], 2), pf(vk["dividend_yield_ttm_pct"], 2), "EquityRT, KAP"),
        ("Risk", "Beta (2 yıl)", "yok", tr(tn["beta_2y"], 2), tr(vk["beta_2y"], 2), "EquityRT"),
    ]
    st.dataframe(pd.DataFrame(ratio_rows, columns=["Grup", "Rasyo", "BRSAN", tn["name"], vk["name"], "Hesap ve kaynak"]), hide_index=True)
    st.caption("BRSAN özsermayesi piyasa değerinin PD/DD'ye bölünmesiyle, toplam aktif EquityRT Peer Performance ekranından alındı (22.09.2026). \"yok\" olan hücreler kaynakta bulunmayan verilerdir, tahminle doldurulmadı.")

    dp = v.dupont(TTM_NI, TTM_REV, TA, BV)
    tn_lev, vk_lev = tn["roe_pct"] / tn["roa_pct"], vk["roe_pct"] / vk["roa_pct"]
    html(
        f'<div class="sac-thesis"><b>DuPont:</b> ROE {pct(dp["roe"])} = net marj {pct(dp["net_marj"])} × aktif devir hızı '
        f'{tr(dp["aktif_devir"], 2)}x × finansal kaldıraç {tr(dp["kaldirac"], 2)}x. Karşılaştırma: Tenaris ROE %{tr(tn["roe_pct"])}, '
        f'Vallourec %{tr(vk["roe_pct"])}. BRSAN\'ın finansal kaldıracı, Tenaris\'in yaklaşık {tr(tn_lev, 2)}x ve Vallourec\'in yaklaşık '
        f'{tr(vk_lev, 2)}x seviyesinin (ROE ÷ ROA) üstünde. Yani ROE\'yi borçla büyütme alanı yok; ROE\'yi taşıyacak asıl kaldıraç net marj. '
        'Bu da tezin sorusuyla aynı yere çıkıyor: marj kalıcı mı?</div>'
    )

    st.markdown("#### Sermaye dağılımı: nakit nereye gitti? (1Y26)")
    steps = [
        ("2025 sonu kasa", CF["kasa_2025"], "Kasa"),
        ("Faaliyetlerden", CF["faaliyet_nakdi"], "Giriş"),
        ("Yatırım", CF["yatirim_nakit_cikisi"], "Çıkış"),
        ("Finansman", CF["finansman_nakit_cikisi"], "Çıkış"),
        ("2Ç26 sonu kasa", CF["kasa_2c26"], "Kasa"),
    ]
    wf, run = [], 0.0
    for name, val, kind in steps:
        if kind == "Kasa":
            wf.append({"adim": name, "y": 0, "y2": val, "tur": kind, "lbl": tr(val, 0)})
            run = val
        else:
            wf.append({"adim": name, "y": run, "y2": run + val, "tur": kind, "lbl": f"{'+' if val > 0 else ''}{tr(val, 0)}"})
            run += val
    wdf = pd.DataFrame(wf)
    wbars = alt.Chart(wdf).mark_bar(size=54, cornerRadius=4).encode(
        x=alt.X("adim:N", sort=[s[0] for s in steps], title=None, axis=alt.Axis(labelAngle=0)),
        y=alt.Y("y:Q", title="mn $"), y2="y2:Q",
        color=alt.Color("tur:N", scale=alt.Scale(domain=["Kasa", "Giriş", "Çıkış"], range=[LAV, "#3E9A72", "#D9546A"]), legend=alt.Legend(orient="bottom", title=None)),
    )
    wtxt = alt.Chart(wdf).mark_text(dy=-8, color=PLUM, fontWeight="bold").encode(
        x=alt.X("adim:N", sort=[s[0] for s in steps]), y=alt.Y("y2:Q"), text="lbl:N"
    )
    wc1, wc2 = st.columns([3, 2])
    wc1.altair_chart((wbars + wtxt).properties(height=280), width="stretch")
    wc2.markdown(md(
        f"- Faaliyetlerden {tr(CF['faaliyet_nakdi'], 0)} mn $ nakit girdi, {tr(-CF['yatirim_nakit_cikisi'], 0)} mn $'ı yatırıma gitti; "
        f"yatırım harcaması gelirin {pct(capex_rev)}'ü.\n"
        f"- Net borç bir yılda {tr(P['2Ç25']['net_borc'], 0)} mn $'dan {tr(ND, 0)} mn $'a indi, kasa {tr(CF['kasa_2c26'], 0)} mn $'a çıktı.\n"
        "- Ortaklara dağıtım yok: 2025 kârı dağıtılmadı (yasal kayıtlarda TMS 29 kaynaklı zarar).\n"
        "- **Okuma:** Sermaye önce bilançoya ve büyüme yatırımına gidiyor. Jürinin soracağı soru: bu yatırımın getirisi (ROIC) "
        "sermaye maliyetini aşıyor mu? Yatırılan sermaye KAP bilançosundan eklenince ROIC ile WACC yan yana konacak."
    ))
    st.caption(f"Kaynak: {CF['kaynak']}. {CF['not']}")

    st.markdown("##### Kaynak tablo")
    tbl = pd.DataFrame([
        {"Dönem": k, "Gelir": tr(d["gelir"]), "FAVÖK": tr(d["favok"]), "FAVÖK marjı": pct(d["favok"] / d["gelir"]),
         "Net kâr": tr(d["net_kar"]), "Net borç": tr(d["net_borc"], 0) if "net_borc" in d else ""}
        for k, d in P.items()
    ])
    st.dataframe(tbl, hide_index=True)
    st.caption(
        f"Kaynak: {FIN['kaynak']}. [1Ç26 sunumu]({SRC['d1c26']['url']}) · [2Ç26 sunumu]({SRC['d2c26']['url']}). "
        "Yüzdeler yuvarlanmış sunum rakamlarından hesaplandı; sunumdaki yüzdelerle ondalıkta fark olabilir."
    )

# 4. RİSK MATRİSİ
with tabs[3]:
    st.caption(
        "Olasılık ve etki puanları veri değil, analist yargısıdır (1 düşük, 5 yüksek). Jüride savunabileceğin şekilde "
        "tablodan değiştir; grafik anında güncellenir. Kazanan raporlarda her riskin yanında bir azaltıcı durur, burada da öyle."
    )
    rdf0 = pd.DataFrame([{"Risk": r["risk"], "Olasılık": r["olasilik"], "Etki": r["etki"]} for r in PITCH["risks"]])
    rdf = st.data_editor(
        rdf0, hide_index=True, disabled=["Risk"], key="risk_editor", width="stretch",
        column_config={
            "Olasılık": st.column_config.NumberColumn(min_value=1, max_value=5, step=1),
            "Etki": st.column_config.NumberColumn(min_value=1, max_value=5, step=1),
        },
    )
    plot = rdf.copy()
    plot["Skor"] = plot["Olasılık"] * plot["Etki"]
    # Aynı hücreye düşen riskleri küçük sabit kaydırmalarla ayır ki etiketler üst üste binmesin
    offsets = [(0, 0), (0.22, -0.24), (-0.22, 0.24), (0.22, 0.24), (-0.22, -0.24)]
    seen: dict = {}
    xs, ys = [], []
    for _, r in plot.iterrows():
        key = (r["Olasılık"], r["Etki"])
        k = seen.get(key, 0)
        seen[key] = k + 1
        dx, dy = offsets[k % len(offsets)]
        xs.append(r["Olasılık"] + dx)
        ys.append(r["Etki"] + dy)
    plot["x"], plot["y"] = xs, ys
    zones = pd.DataFrame([
        {"x": 0.5, "x2": 5.5, "y": 0.5, "y2": 5.5, "z": "a"},
    ])
    zone = alt.Chart(zones).mark_rect(color="#FFF8FB", stroke="#F0D5E6").encode(x="x:Q", x2="x2:Q", y="y:Q", y2="y2:Q")
    diag = alt.Chart(pd.DataFrame({"x": [0.5, 5.5], "y": [5.5, 0.5]})).mark_line(color="#F0D5E6", strokeDash=[4, 4]).encode(x="x:Q", y="y:Q")
    dots = alt.Chart(plot).mark_circle(opacity=0.9, stroke="white", strokeWidth=2).encode(
        x=alt.X("x:Q", title="Olasılık", scale=alt.Scale(domain=[0.5, 5.5]), axis=alt.Axis(values=[1, 2, 3, 4, 5])),
        y=alt.Y("y:Q", title="Etki", scale=alt.Scale(domain=[0.5, 5.5]), axis=alt.Axis(values=[1, 2, 3, 4, 5])),
        size=alt.Size("Skor:Q", scale=alt.Scale(range=[300, 1400]), legend=None),
        color=alt.Color("Skor:Q", scale=alt.Scale(domain=[1, 25], range=["#E7C9DD", "#B23A48"]), legend=None),
        tooltip=["Risk:N", "Olasılık:Q", "Etki:Q", "Skor:Q"],
    )
    dtxt = alt.Chart(plot).mark_text(align="left", dx=16, fontSize=11, color=PLUM).encode(x="x:Q", y="y:Q", text="Risk:N")
    st.altair_chart((zone + diag + dots + dtxt).properties(height=420), width="stretch")
    by_name = {r["risk"]: r for r in PITCH["risks"]}
    for _, r in plot.sort_values("Skor", ascending=False).iterrows():
        info = by_name[r["Risk"]]
        with st.expander(f"{r['Risk']} · skor {int(r['Skor'])}"):
            st.markdown(md(f"**Kanıt:** {info['kanit']}\n\n**Azaltıcı:** {info['azaltici']}"))

# 5. ESG
with tabs[4]:
    E = PITCH["esg"]
    html(f'<div class="sac-thesis"><b>ESG tezimiz:</b> {E["ozet"]}</div>')
    cols = st.columns(3)
    labels_esg = {"E": "Çevresel", "S": "Sosyal", "G": "Kurumsal yönetim"}
    for col, key in zip(cols, ["E", "S", "G"]):
        with col:
            st.markdown(f"##### {labels_esg[key]}")
            for item in [i for i in E["dogrulanmis"] if i["alan"] == key]:
                src = f'<a href="{item["url"]}" target="_blank">{item["kaynak"]}</a>' if item.get("url") else item["kaynak"]
                html(f'<div class="sac-card"><p>{item["bilgi"]}</p><div class="sac-src">Kaynak: {src}</div></div>')

    st.markdown("#### SASB önemlilik haritası ve değerlemeye bağlantı")
    st.caption("Konular SASB / IFRS S2 Iron & Steel Producers sektör rehberinden; kanıt sütunu kamuya açık verinin bugünkü durumunu gösteriyor.")
    sasb = pd.DataFrame(E["sasb"]).rename(columns={
        "konu": "Konu", "neden": "Neden önemli", "borusan": "Borusan'da durum", "degerleme": "Değerlemeye etkisi", "kanit": "Kanıt"
    })
    st.dataframe(sasb, hide_index=True)
    counts = sasb["Kanıt"].value_counts().to_dict()
    st.caption(
        f"Veri şeffaflığı özeti: {len(sasb)} önemli konunun {counts.get('Kısmi', 0)}'ünde kısmi kanıt, "
        f"{counts.get('Veri yok', 0)}'sinde kamuya açık veri yok. Bu boşluklar TSRS raporunun tam metninden kapatılacak."
    )

    st.markdown("#### ESG maliyetini değerlemeye bağla: karbon maliyeti hesaplayıcı")
    st.caption(
        "Jürinin resmi soru havuzunda şu soru var: ESG kaynaklı maliyetleri değerlemenize nasıl yansıttınız? "
        "Bu hesaplayıcı cevabın iskeleti. Girdiler varsayım; AB gelir payı rakamı PDF'ten teyit edilmeden rapora girmemeli."
    )
    e1, e2, e3 = st.columns(3)
    eu_share = e1.number_input("AB gelir payı (%)", 0.0, 60.0, float(E["ab_gelir_payi"]["deger"]), step=1.0, help=E["ab_gelir_payi"]["not"])
    carbon = e2.number_input("Aktarılamayan karbon maliyeti (AB gelirinin %'si)", 0.0, 15.0, 2.0, step=0.5)
    mult_e = e3.number_input("Uygulanan FD/FAVÖK (x)", 2.0, 20.0, round(EV / E26_MID, 1), step=0.5, help="Varsayılan: bugünkü fiyatın ima ettiği 2026T çarpanı")
    hit = REV_MID * eu_share / 100 * carbon / 100
    eq_hit = hit * mult_e
    z1, z2, z3 = st.columns(3)
    z1.metric("Yıllık FAVÖK etkisi", f"−{tr(hit)} mn $")
    z2.metric("Marj etkisi", f"−{tr(hit / REV_MID * 100, 2)} puan")
    z3.metric("Özsermaye değerine etkisi", f"−{tr(eq_hit, 0)} mn $", delta=pct(-eq_hit / MCAP, 1, sign=True))
    st.markdown("#### ESG'yi iskonto oranına bağla: risk primi hesaplayıcı")
    st.caption(
        f"Jüriler ESG'yi finansal modelden ayrı görmez; burada ESG, WACC'a eklenen bir prim olarak modele giriyor. Baz WACC "
        f"(%{tr(wacc, 2)}) ve büyüme (%{tr(g_term, 2)}) Değerleme Masası'ndaki reverse DCF ayarlarından geliyor. Prim veri değil, "
        "gerekçelendirilmesi gereken bir yargı: düşük halka açıklık, emisyon verisindeki boşluklar, AB karbon düzenlemesine maruziyet."
    )
    prem = st.slider("ESG ve yönetişim risk primi (baz puan)", 0, 200, 50, step=10)
    fcff_base = v.implied_steady_fcff(EV, wacc / 100, g_term / 100)

    def eq_delta(bp: float) -> float:
        return v.ev_from_fcff(fcff_base, wacc / 100 + bp / 10000, g_term / 100) - EV

    p1, p2 = st.columns([1, 2])
    p1.metric("Özsermaye değerine etkisi", f"{tr(eq_delta(prem), 0)} mn $", delta=pct(eq_delta(prem) / MCAP, 1, sign=True))
    p1.caption(md(f"Her 50 baz puan yaklaşık {tr(-eq_delta(50), 0)} mn $ değer siliyor."))
    pdf_ = pd.DataFrame([{"bp": b, "d": eq_delta(b)} for b in range(0, 210, 10)])
    p2.altair_chart(
        alt.Chart(pdf_).mark_area(line={"color": PINK}, color=alt.Gradient(
            gradient="linear", stops=[alt.GradientStop(color="#FBE3F0", offset=0), alt.GradientStop(color=ROSE, offset=1)], x1=1, x2=1, y1=1, y2=0,
        )).encode(x=alt.X("bp:Q", title="Risk primi (baz puan)"), y=alt.Y("d:Q", title="Özsermaye etkisi (mn $)")).properties(height=200),
        width="stretch",
    )
    st.warning("**Veri tuzakları (rapora girmemeli):**\n\n" + "\n".join(f"- {t}" for t in E["tuzaklar"]))

# 6. CFA PUAN HARİTASI
with tabs[5]:
    PB = PITCH["cfa_playbook"]
    st.caption(f"{PB['format']} Kaynak: {src_link('cfa_rules')}")
    STATUS = {"Başlamadı": 0.0, "Taslak": 0.35, "Kanıt hazır": 0.7, "Rapora hazır": 1.0}
    defaults = ["Kanıt hazır", "Taslak", "Taslak", "Kanıt hazır", "Kanıt hazır", "Kanıt hazır", "Taslak"]
    wr = pd.DataFrame([
        {"Bölüm": r["bolum"], "Puan": r["puan"], "Durum": d, "Uygulamadaki kanıt": r["kanit"]}
        for r, d in zip(PB["yazili_rubrik"], defaults)
    ])
    cL, cR = st.columns([3, 2])
    with cL:
        st.markdown("##### Yazılı rapor rubriği (100 puan)")
        wr_ed = st.data_editor(
            wr, hide_index=True, disabled=["Bölüm", "Puan", "Uygulamadaki kanıt"], key="rubric_editor", width="stretch",
            column_config={"Durum": st.column_config.SelectboxColumn(options=list(STATUS.keys()), required=True)},
        )
        weighted = sum(r["Puan"] * STATUS[r["Durum"]] for _, r in wr_ed.iterrows())
        st.progress(min(weighted / 100, 1.0), text=f"Puan ağırlıklı hazırlık: {tr(weighted, 0)} / 100")
        st.caption("Durumlar Selin'in kendi değerlendirmesi; ağırlıklar resmi rubrikten. En yüksek puanlı iki bölüm Değerleme ve Finansal Analiz (20+20).")
    with cR:
        st.markdown("##### Sunum rubriği (100 puan)")
        sr = pd.DataFrame(PB["sunum_rubrik"])
        sbars = alt.Chart(sr).mark_bar(color=PINK, cornerRadiusEnd=6, size=20).encode(
            y=alt.Y("bolum:N", sort="-x", title=None, axis=alt.Axis(labelLimit=200)), x=alt.X("puan:Q", title="Puan")
        )
        st.altair_chart((sbars + sbars.mark_text(align="left", dx=5, color=PLUM).encode(text="puan:Q")).properties(height=250), width="stretch")
        st.caption("Soru cevap tek başına 20 puan. Jüri Provası sekmesi tam bunun için.")

    st.markdown("##### Kazanan raporlarda tekrar eden desenler")
    st.caption(f"İncelenen: {src_link('waterloo')} · {src_link('niu')}")
    have = [p["desen"] for p in PB["kazanan_desenler"] if p["bizde"]]
    todo = [p["desen"] for p in PB["kazanan_desenler"] if not p["bizde"]]
    k1, k2 = st.columns(2)
    k1.markdown("**Bu cockpit'te hazır**\n\n" + "\n".join(f"- ✅ {h}" for h in have))
    k2.markdown("**Rapor sürecinde eklenecek**\n\n" + "\n".join(f"- ⏳ {t}" for t in todo))

# 7. JÜRİ PROVASI
with tabs[6]:
    PB = PITCH["cfa_playbook"]
    st.markdown("##### Jüri rehberindeki resmi örnek sorular")
    st.caption(f"Kaynak: {src_link('cfa_judge')}. Jüri sunumu, alım tarafının satış tarafını dinlediği gözle değerlendirir.")
    for q in PB["resmi_juri_sorulari"]:
        st.markdown(f"- *{q}*")

    st.markdown("##### Prova: önce kendin cevapla, sonra iskeleti aç")
    for i, q in enumerate(PITCH["jury_questions"]):
        with st.expander(f"❓ {q['soru']}"):
            st.text_area("Senin cevabın", key=f"jury_ans_{i}", height=90, placeholder="30 saniyelik cevabını buraya yaz...")
            if st.toggle("Cevap iskeletini göster", key=f"jury_show_{i}"):
                st.markdown(md("\n".join(f"- {b}" for b in q["iskelet"])))
                st.error(md(f"**Tuzak:** {q['tuzak']}"))

    st.markdown("##### 60 saniyelik İngilizce pitch")
    pitch = (
        f"Borusan Boru is a Turkish steel pipe maker with ten plants on three continents and {PITCH['meta']['kapasite'].replace(',', '.').replace(' milyon ton', ' million tons')} "
        f"of capacity; {SEG['abd_gelir_payi']['1Y26']}% of its first half 2026 revenue came from the United States. "
        f"Three facts frame our work. First, visibility: management raised 2026 guidance to {REV_LO / 1000:.1f} to {REV_HI / 1000:.1f} billion dollars "
        f"of revenue at a {M_LO * 100:.0f} to {M_HI * 100:.0f}% EBITDA margin, backed by an infrastructure order book of about 2.6 billion dollars "
        f"and roughly {NEW_ORDERS:,.0f} million dollars of new US orders announced in August. "
        f"Second, a repaired balance sheet: net debt to EBITDA fell from {LEV['2Ç25']:.1f}x to {LEV['2Ç26']:.1f}x in a year. "
        f"Third, the debate: on trailing numbers the stock trades at about {EV / TTM_EBITDA:.1f}x EV/EBITDA, well above Tenaris and Vallourec, "
        f"but on the midpoint of the new guidance it is close to {EV / E26_MID:.1f}x, near Tenaris. "
        "So the question our report answers is simple: is the 11.5% second quarter margin the new normal, or a one off project mix? "
        "If it holds, the premium is earned. If it fades, that is the key risk."
    )
    st.markdown(f"> {pitch}")
    st.caption("Rakamlar sayfadaki hesaplardan otomatik geliyor; veri güncellenince pitch de güncellenir.")

    st.markdown("##### 10 dakikalık sunum akışı (sunum rubriğine göre)")
    flow = pd.DataFrame([
        {"Süre": "1,5 dk", "Bölüm": "Tavsiye ve tez", "Rubrikteki karşılığı": "Presentation (20)"},
        {"Süre": "1,5 dk", "Bölüm": "Şirket, sektör, peer seçimi", "Rubrikteki karşılığı": "Presentation / Financial Analysis"},
        {"Süre": "2,5 dk", "Bölüm": "Finansal analiz: marj, kaldıraç, nakit kalitesi", "Rubrikteki karşılığı": "Financial Analysis (20)"},
        {"Süre": "2,5 dk", "Bölüm": "Değerleme: football field, senaryo, reverse DCF", "Rubrikteki karşılığı": "Valuation (20)"},
        {"Süre": "1 dk", "Bölüm": "Riskler ve azaltıcılar", "Rubrikteki karşılığı": "Presentation"},
        {"Süre": "1 dk", "Bölüm": "ESG ve değerlemeye etkisi", "Rubrikteki karşılığı": "ESG (10)"},
    ])
    st.dataframe(flow, hide_index=True)

st.markdown("---")
st.caption(
    "SS Academic Coach · Borusan Equity Cockpit. Hesap çekirdeği utils/valuation.py içinde ve birim testli; veriler "
    "data/brsan_pitch.json ile data/cfa_peers.json dosyalarında, her biri kaynağıyla. Hiçbir rakam tahminle doldurulmadı."
)
