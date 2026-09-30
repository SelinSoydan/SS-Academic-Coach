import json
import random
import statistics
from html import escape
from pathlib import Path
from urllib.parse import urlencode

import altair as alt
import pandas as pd
import streamlit as st

from utils import valuation as v
from utils.i18n import L, fill, is_en, lang, load_localized, num, period, pp
from utils.team_board import get_board
from utils.theme import inject_theme

st.set_page_config(page_title="Borusan Equity Cockpit", page_icon="🏆", layout="wide")
inject_theme()

ROOT = Path(__file__).parent.parent
PITCH = load_localized("brsan_pitch.json")
PEERS = json.loads((ROOT / "data" / "cfa_peers.json").read_text(encoding="utf-8"))
GLOSS = json.loads((ROOT / "data" / "metric_glossary.json").read_text(encoding="utf-8"))
SRC = PITCH["sources"]
APP_URL = "https://ss-academic-coach.streamlit.app/Borusan_Equity_Cockpit"
LG = lang()

PINK, PLUM, LAV, ROSE, MAUVE = "#C2578B", "#4A2E45", "#B39DDB", "#E58FB3", "#8E6C8A"
RED, GREEN = "#D9546A", "#3E9A72"
NUM_AXIS = alt.Axis() if is_en() else alt.Axis(labelExpr="replace(datum.label, ',', '.')")


def pct(x: float, d: int = 1, sign: bool = False) -> str:
    s = pp(x * 100, d)
    return "+" + s if sign and x > 0 else s


def money(x: float, d: int = 1) -> str:
    return f"${num(x, d)}m" if is_en() else f"{num(x, d)} mn $"


def bn_range(a: float, b: float) -> str:
    return f"${num(a / 1000)} to {num(b / 1000)}bn" if is_en() else f"{num(a / 1000)} ile {num(b / 1000)} mlr $"


def bn_one(a: float) -> str:
    return f"${num(a / 1000)}bn" if is_en() else f"{num(a / 1000)} mlr $"


def md(s: str) -> str:
    """Markdown metninde $ işaretini kaçırır; yoksa iki $ arası LaTeX formülü gibi render ediliyor."""
    return s.replace("$", "\\$")


def raw(s: str) -> None:
    st.markdown(s, unsafe_allow_html=True)


def src_link(key: str) -> str:
    s = SRC[key]
    return f"[{s['ad']}]({s['url']})" if s.get("url") else s["ad"]


def card(pill: str, pill_cls: str, title: str, big: str, body: str, src: str) -> str:
    return (
        f'<div class="sac-card"><span class="sac-pill {pill_cls}">{pill}</span>'
        f'<h4>{title}</h4><div class="sac-big">{big}</div><p>{body}</p>'
        f'<div class="sac-src">{L("Kaynak", "Source")}: {src}</div></div>'
    )


def gl(key: str, other: bool = False) -> dict:
    side = ("tr" if is_en() else "en") if other else ("en" if is_en() else "tr")
    return GLOSS[key][side]


def gl_help(key: str) -> str:
    g = gl(key)
    return md(f"**{g['soru']}** {g['aciklama']}")


QP = st.query_params


def qf(name: str, default: float, lo: float, hi: float) -> float:
    """Paylaşılan senaryo linkindeki değeri okur; yoksa ya da aralık dışındaysa varsayılana döner."""
    try:
        val = float(QP.get(name, default))
    except (TypeError, ValueError):
        return default
    return val if lo <= val <= hi else default


# Çekirdek metrikler: her rakam JSON'daki kaynaklı veriden türetiliyor
FIN = PITCH["financials"]
P = FIN["donemler"]
BASE = FIN["ttm_bazi"]


def ttm_of(key: str) -> float:
    return v.ttm(P[BASE["yil"]][key], P[BASE["onceki"]][key], P[BASE["guncel"]][key])


TTM_REV, TTM_EBITDA, TTM_NI = ttm_of("gelir"), ttm_of("favok"), ttm_of("net_kar")
NB = FIN["net_borc_donemi"]
ND = P[NB]["net_borc"]
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
PEER_NAMES = L(" ve ", " and ").join(p["name"].replace(" SA", "") for p in NARROW)
SECTOR = PEERS["sector_median"]
LEV = FIN["kaldirac_serisi"]["degerler"]
SEG = PITCH["segmentler_1y26"]
US_SHARE = SEG["abd_gelir_payi"]["1Y26"]
CF = FIN["nakit_akisi_1y26"]
BACKLOG = PITCH["siparisler"][0]["tutar_mn_usd"]
NEW_ORDERS = sum(o["tutar_mn_usd"] for o in PITCH["siparisler"] if o["tarih"].startswith("2026-08"))
BV = MCAP / MKT["p_bv"]
TA = PEERS["target"]["total_assets_mn_usd"]
DP = v.dupont(TTM_NI, TTM_REV, TA, BV)
REC = {"BUY": L("AL", "BUY"), "HOLD": L("TUT", "HOLD"), "SELL": L("SAT", "SELL")}


@st.cache_data(show_spinner=False)
def monte_carlo(rev_r: tuple, mar_r: tuple, mul_r: tuple, nd: float, n: int = 10000, seed: int = 42) -> list:
    rng = random.Random(seed)
    return sorted(
        v.equity_from_ev_multiple(rng.uniform(*mul_r), rng.uniform(*rev_r) * rng.uniform(*mar_r) / 100, nd)
        for _ in range(n)
    )


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


# Varsayılanlar: paylaşılan linkten gelirse onu, yoksa rehberlik ve peer değerlerini kullan
D_REV = (int(qf("rlo", REV_LO, 1800, 2800)), int(qf("rhi", REV_HI, 1800, 2800)))
D_MAR = (qf("mlo", M_LO * 100, 5.0, 14.0), qf("mhi", M_HI * 100, 5.0, 14.0))
D_MUL = (qf("xlo", float(min(PEER_FWD)), 3.0, 16.0), qf("xhi", float(max(PEER_FWD)), 3.0, 16.0))
D_W, D_G = qf("w", 11.0, 7.0, 15.0), qf("g", 2.5, 0.0, 4.0)
SS = st.session_state
CUR_W, CUR_G = SS.get("rd_wacc", D_W), SS.get("rd_g", D_G)
CUR_SIMS = monte_carlo(tuple(SS.get("mc_rev", D_REV)), tuple(SS.get("mc_mar", D_MAR)), tuple(SS.get("mc_mul", D_MUL)), ND)
CUR_FCFF = v.implied_steady_fcff(EV, CUR_W / 100, CUR_G / 100)

GV = {
    "pe": num(MKT["p_e"], 2), "ey": pct(1 / MKT["p_e"]), "sector_pe": num(SECTOR["p_e"], 2),
    "ev_ebitda_ttm": num(EV / TTM_EBITDA), "ev_ebitda_fwd": num(EV / E26_MID),
    "tenaris_fwd": num(PEER_FWD[0]), "vallourec_fwd": num(PEER_FWD[1]),
    "nd_ebitda": num(ND / TTM_EBITDA, 2), "lev_2q25": num(LEV["2Ç25"]),
    "pbv": num(MKT["p_bv"], 2), "bv": num(BV, 0), "roe": pct(DP["roe"]), "nm": pct(DP["net_marj"]),
    "at": num(DP["aktif_devir"], 2), "em": num(DP["kaldirac"], 2),
    "wacc": pp(CUR_W, 2), "g": pp(CUR_G, 2), "fcff": num(CUR_FCFF, 0), "conv": pct(CUR_FCFF / E26_MID, 0),
    "mc_p50": num(CUR_SIMS[len(CUR_SIMS) // 2], 0), "mc_prob": pct(sum(1 for s in CUR_SIMS if s > MCAP) / len(CUR_SIMS), 1),
    "fcf": num(CF["serbest_nakit_akimi"], 0), "cash_conv": pct(CF["serbest_nakit_akimi"] / P["1Y26"]["favok"], 0),
    "wc": num(CF["isletme_sermayesi"], 0), "ttm_ebitda": num(TTM_EBITDA), "ttm_ni": num(TTM_NI),
    "esg50": num(EV - v.ev_from_fcff(CUR_FCFF, CUR_W / 100 + 0.005, CUR_G / 100), 0),
}

ME = SS.get("me_name", "").strip()

# HERO
quote = live_quote()


def kpi(label: str, value: str, sub: str, key: str = None) -> str:
    tip = f' title="{escape(gl(key)["soru"])}"' if key else ""
    mark = ' <span style="opacity:.65">ⓘ</span>' if key else ""
    return f'<div class="sac-kpi"{tip}><div class="l">{label}{mark}</div><div class="v">{value}</div><div class="s">{sub}</div></div>'


kpis = [
    kpi(L("Piyasa değeri", "Market value"), money(MCAP), f"EquityRT, {MKT['tarih']}"),
    kpi(L("Firma değeri", "Enterprise value"), money(EV), L(f"PD + {period(NB)} net borç", f"MV + {period(NB)} net debt"), "ev_ebitda"),
    kpi(L("FD/FAVÖK son 12 ay", "EV/EBITDA TTM"), f"{num(EV / TTM_EBITDA)}x", BASE["etiket"], "ev_ebitda"),
    kpi(L("FD/FAVÖK 2026T", "EV/EBITDA 2026E"), f"{num(EV / E26_MID)}x", L("yükseltilmiş rehberliğin ortası", "midpoint of raised guidance"), "ev_ebitda"),
    kpi(L("F/K", "P/E"), num(MKT["p_e"], 2), L("mutabakat: ", "reconciled: ") + num(MCAP / TTM_NI, 2), "pe"),
    kpi(L("Net borç / FAVÖK", "Net debt / EBITDA"), f"{num(ND / TTM_EBITDA, 2)}x",
        L(f"sunumda {num(LEV['2Ç26'])}x · 2Ç25'te {num(LEV['2Ç25'])}x", f"deck: {num(LEV['2Ç26'])}x · 2Q25: {num(LEV['2Ç25'])}x"), "nd_ebitda"),
]
if quote:
    chg = quote["price"] / quote["prev"] - 1 if quote["prev"] else 0
    kpis.append(kpi(L("Canlı fiyat", "Live price"), f"{num(quote['price'], 2)} {quote['cur']}", f"{pct(chg, 2, sign=True)} · yfinance, {L('gecikmeli', 'delayed')}"))
raw(
    '<div class="sac-hero">'
    '<div class="sac-eyebrow">CFA Institute Research Challenge 2026/27 · Equity Research Cockpit</div>'
    f'<div class="sac-hero-title">Borusan Boru<span>BIST: {PITCH["meta"]["ticker"]}</span></div>'
    f'<div class="sac-hero-sub">{PITCH["meta"]["endustri"]}. {PITCH["meta"]["tesis"]}. '
    + L(f"{PITCH['meta']['kapasite']} kapasite, 1Y26 gelirinin %{US_SHARE}'i ABD'den. Buradaki her rakamın kaynağı belli, her hesabın formülü açık.",
        f"{PITCH['meta']['kapasite']} of capacity; {US_SHARE}% of 1H26 revenue came from the US. Every number here has a source, every calculation an open formula.")
    + f'</div><div class="sac-kpi-grid">{"".join(kpis)}</div></div>'
)

st.markdown("##### 📖 " + L("Metrik rehberi: her rasyo hangi soruyu cevaplıyor?", "Metric guide: which question does each ratio answer?"))
GKEYS = ["pe", "ev_ebitda", "pe_vs_ev", "nd_ebitda", "pbv", "roe_dupont", "roic",
         "wacc", "reverse_dcf", "monte_carlo", "football_field", "fcf_conversion", "ttm", "esg_premium"]
for row in (GKEYS[:7], GKEYS[7:]):
    for col, key in zip(st.columns(len(row)), row):
        g, o = gl(key), gl(key, other=True)
        with col.popover(f"ℹ️ {g['baslik']}"):
            st.markdown(md(f"**{g['soru']}**"))
            st.markdown(md(g["aciklama"]))
            st.info(md(fill(g["brsan"], GV)))
            st.caption(md(f"{L('Tuzak', 'Trap')}: {g['tuzak']}"))
            st.divider()
            st.caption(md(f"**{L('English', 'Türkçe')}.** {o['soru']} {o['aciklama']}"))

tabs = st.tabs([
    "🎯 " + L("Yatırım Tezi", "Investment Thesis"),
    "📊 " + L("Değerleme Masası", "Valuation Desk"),
    "📈 " + L("Finansal Analiz", "Financial Analysis"),
    "⚠️ " + L("Risk Matrisi", "Risk Matrix"),
    "🌱 ESG",
    "🏆 " + L("CFA Puan Haritası", "CFA Scoring Map"),
    "🎤 " + L("Jüri Provası", "Jury Rehearsal"),
    "👥 " + L("Takım Masası", "Team Desk"),
])

# 1. YATIRIM TEZİ
with tabs[0]:
    raw('<div class="sac-thesis"><b>' + L("Tezin sorusu tek cümlede:", "The thesis question in one sentence:") + "</b> " + L(
        "Piyasa BRSAN'ı geçmiş kâra göre peer'larından belirgin pahalı, yükseltilmiş 2026 rehberliğine göre ise Tenaris'e yakın fiyatlıyor. "
        "Raporun işi, 2Ç26'daki %11,5 marjın ve sipariş portföyünün kalıcı kârlılığa dönüşüp dönüşmeyeceğini test etmek.",
        "The market prices BRSAN clearly above its peers on trailing profit, but close to Tenaris on its raised 2026 guidance. "
        "The report's job is to test whether the 11.5% margin of 2Q26 and the order backlog turn into durable profitability.") + "</div>")
    g_lo, g_hi = v.growth(REV_LO, P["2025"]["gelir"]), v.growth(REV_HI, P["2025"]["gelir"])
    pg = G["onceki"]["gelir_mn_usd"]
    c1, c2, c3 = st.columns(3)
    c1.markdown(card(
        L("LEHTE", "SUPPORTS"), "green", L("Büyüme görünürlüğü", "Growth visibility"), bn_range(REV_LO, REV_HI),
        L(f"2026 gelir rehberliği, 2025'e göre {pct(g_lo, 0)} ile {pct(g_hi, 0)} büyüme demek. Rehberlik 2Ç26'da yukarı çekildi (önce {bn_range(*pg)}). "
          f"Altyapı ve Proje sipariş portföyü yaklaşık {bn_one(BACKLOG)}, Ağustos'ta buna yaklaşık {money(NEW_ORDERS, 0)} yeni ABD siparişi eklendi.",
          f"2026 revenue guidance implies {pct(g_lo, 0)} to {pct(g_hi, 0)} growth over 2025. Guidance was raised in 2Q26 (previously {bn_range(*pg)}). "
          f"The Infrastructure & Project backlog is about {bn_one(BACKLOG)}, and roughly {money(NEW_ORDERS, 0)} of new US orders followed in August."),
        L("2Ç26 sunumu s.3 ve s.23, KAP", "2Q26 deck p.3 and p.23, KAP"),
    ), unsafe_allow_html=True)
    c2.markdown(card(
        L("LEHTE", "SUPPORTS"), "green", L("Bilanço onarımı", "Balance sheet repair"), f"{num(LEV['2Ç25'])}x → {num(LEV['2Ç26'])}x",
        L(f"Net borç/FAVÖK bir yılda {num(LEV['2Ç25'])}x'ten {num(LEV['2Ç26'])}x'e indi. Net borç {money(ND, 0)}, kasa {money(CF['kasa_2c26'], 0)}. "
          f"1Y26 serbest nakit akımı {money(CF['serbest_nakit_akimi'], 0)}, ama {money(CF['isletme_sermayesi'], 0)}'ı işletme sermayesinden geldi.",
          f"Net debt to EBITDA fell from {num(LEV['2Ç25'])}x to {num(LEV['2Ç26'])}x in a year. Net debt is {money(ND, 0)}, cash {money(CF['kasa_2c26'], 0)}. "
          f"1H26 free cash flow was {money(CF['serbest_nakit_akimi'], 0)}, but {money(CF['isletme_sermayesi'], 0)} of it came from working capital."),
        L("2Ç26 sunumu s.21 ve s.22", "2Q26 deck p.21 and p.22"),
    ), unsafe_allow_html=True)
    c3.markdown(card(
        L("SORGULA", "QUESTION"), "amber", L("Değerleme ve yoğunlaşma", "Valuation and concentration"), f"{num(EV / TTM_EBITDA)}x",
        L(f"Son 12 ay FD/FAVÖK. Aynı çarpan Tenaris'te {num(PEER_TTM[0])}x, Vallourec'te {num(PEER_TTM[1])}x. Gelirin %{US_SHARE}'i tek ülkeden geliyor. "
          "Prim ancak marj kalıcı olursa hak ediliyor.",
          f"Trailing EV/EBITDA. The same multiple is {num(PEER_TTM[0])}x for Tenaris and {num(PEER_TTM[1])}x for Vallourec. {US_SHARE}% of revenue comes "
          "from a single country. The premium is only earned if the margin proves durable."),
        L("EquityRT 22.09.2026, 2Ç26 sunumu", "EquityRT 22.09.2026, 2Q26 deck"),
    ), unsafe_allow_html=True)

    st.markdown("#### " + L("Farkımız nerede olmalı? FaVeS çerçevesi", "Where should our edge be? The FaVeS framework"))
    st.caption(L(
        "Valentine'ın CFA Institute RC kaynakları arasındaki kitabına göre konsensüs dışı bir görüş, tahminde, değerlemede ya da piyasa duygusunda "
        "somut bir üstünlüğe dayanmalı. Aşağıdakiler bizim önerdiğimiz çalışma hatları.",
        "According to Valentine's book, listed among CFA Institute's RC resources, an out of consensus view must rest on a concrete edge in forecast, "
        "valuation or sentiment. These are the lines of work we propose."))
    for col, fv in zip(st.columns(3), PITCH["cfa_playbook"]["faves"]):
        col.markdown(card("EDGE", "", fv["harf"], "", fv["fikir"], src_link("valentine")), unsafe_allow_html=True)

    st.markdown("#### " + L("Katalizör takvimi", "Catalyst calendar"))
    items = "".join(
        f'<div class="sac-tl-item {"future" if c["tur"] == "gelecek" else ""}">'
        f'<div class="sac-tl-date">{c["tarih"]}</div><div>{c["olay"]}</div><div class="sac-src">{c["kaynak"]}</div></div>'
        for c in PITCH["catalysts"]
    )
    raw(f'<div class="sac-tl">{items}</div>')
    st.caption(md(PITCH["siparis_notu"]))

    st.markdown("#### " + L("Fiyatı ne hareket ettirir? Yukarı ve aşağı katalizörler", "What moves the price? Upside and downside catalysts"))
    KY = PITCH["katalizor_yonu"]
    st.caption(KY["not"])
    cu, cdn = st.columns(2)
    for col, items_k, cls, label in ((cu, KY["yukari"], "green", L("▲ YUKARI", "▲ UPSIDE")), (cdn, KY["asagi"], "amber", L("▼ AŞAĞI", "▼ DOWNSIDE"))):
        with col:
            for k in items_k:
                raw(f'<div class="sac-card"><span class="sac-pill {cls}">{label}</span>'
                    f'<h4 style="font-size:1.12rem">{k["olay"]}</h4><p>{k["izle"]}</p></div>')

# 2. DEĞERLEME MASASI
with tabs[1]:
    st.markdown("#### " + L("Football field: çarpanlar bugünkü fiyat hakkında ne söylüyor?", "Football field: what do multiples say about today's price?"))
    st.caption(md(L(
        f"Dar peer grubu: {PEER_NAMES} (EquityRT, 22.09.2026). Firma değeri çarpanlarında özsermaye = çarpan x FAVÖK eksi {money(ND, 0)} net borç. "
        "F/K ve PD/DD'de özsermaye = piyasa değeri x (peer çarpanı / BRSAN çarpanı).",
        f"Narrow peer group: {PEER_NAMES} (EquityRT, 22.09.2026). For EV multiples, equity = multiple x EBITDA minus {money(ND, 0)} of net debt. "
        "For P/E and P/B, equity = market value x (peer multiple / BRSAN multiple).")))
    GR_EV, GR_EQ, GR_SEC = L("Firma değeri çarpanı", "EV multiple"), L("Özsermaye çarpanı", "Equity multiple"), L("Geniş sektör (bağlam)", "Broad sector (context)")

    def rel(own: float, peer: float) -> float:
        return v.equity_from_relative_multiple(MCAP, own, peer)

    ff_rows = [
        (L("FD/FAVÖK son 12 ay, dar peer", "EV/EBITDA TTM, narrow peers"), min(PEER_TTM) * TTM_EBITDA - ND, max(PEER_TTM) * TTM_EBITDA - ND, GR_EV),
        (L("FD/FAVÖK 2026T, dar peer x rehberlik", "EV/EBITDA 2026E, peers x guidance"), min(PEER_FWD) * E26_LO - ND, max(PEER_FWD) * E26_HI - ND, GR_EV),
        (L("F/K son 12 ay, dar peer", "P/E TTM, narrow peers"), rel(MKT["p_e"], min(PEER_PE)), rel(MKT["p_e"], max(PEER_PE)), GR_EQ),
        (L("PD/DD, dar peer", "P/B, narrow peers"), rel(MKT["p_bv"], min(PEER_PB)), rel(MKT["p_bv"], max(PEER_PB)), GR_EQ),
        (L("F/K, geniş sektör medyanı", "P/E, broad sector median"), rel(MKT["p_e"], SECTOR["p_e"]), rel(MKT["p_e"], SECTOR["p_e"]), GR_SEC),
        (L("PD/DD, geniş sektör medyanı", "P/B, broad sector median"), rel(MKT["p_bv"], SECTOR["p_bv"]), rel(MKT["p_bv"], SECTOR["p_bv"]), GR_SEC),
    ]
    ff = pd.DataFrame([
        {"yontem": r[0], "low": r[1], "high": r[2], "grup": r[3],
         "etiket": num(r[1], 0) if abs(r[2] - r[1]) < 1 else f"{num(r[1], 0)} {L('ile', 'to')} {num(r[2], 0)}"}
        for r in ff_rows
    ])
    color = alt.Color("grup:N", scale=alt.Scale(domain=[GR_EV, GR_EQ, GR_SEC], range=[PINK, MAUVE, LAV]), legend=alt.Legend(orient="bottom", title=None))
    base = alt.Chart(ff).encode(y=alt.Y("yontem:N", sort=None, title=None, axis=alt.Axis(labelLimit=280)))
    x_dom = [min(ff["low"].min(), MCAP) * 0.8, max(ff["high"].max(), MCAP) * 1.22]
    bars = base.mark_bar(size=22, cornerRadius=6).encode(
        x=alt.X("low:Q", title=L("Özsermaye değeri (mn $)", "Equity value ($m)"), scale=alt.Scale(domain=x_dom, nice=False), axis=NUM_AXIS),
        x2="high:Q", color=color,
        tooltip=[alt.Tooltip("yontem:N", title=L("Yöntem", "Method")), alt.Tooltip("etiket:N", title=L("Aralık (mn $)", "Range ($m)"))],
    )
    points = base.mark_point(filled=True, size=160, shape="diamond").encode(x="low:Q", color=color).transform_filter("abs(datum.high - datum.low) < 1")
    labels = base.mark_text(align="left", dx=8, color=PLUM, fontSize=11).encode(x="high:Q", text="etiket:N")
    rule_df = pd.DataFrame({"x": [MCAP], "t": [L(f"Bugünkü piyasa değeri {num(MCAP, 0)}", f"Market value today {num(MCAP, 0)}")]})
    rule = alt.Chart(rule_df).mark_rule(color=PLUM, strokeDash=[6, 4], size=2).encode(x="x:Q")
    rule_txt = alt.Chart(rule_df).mark_text(align="right", dx=-6, dy=8, color=PLUM, fontWeight="bold").encode(x="x:Q", y=alt.value(0), text="t:N")
    st.altair_chart((bars + points + labels + rule + rule_txt).properties(height=320), width="stretch")
    st.info(md(L(
        "**Okuma:** Geriye dönük her çarpanda bugünkü piyasa değeri peer aralığının üstünde kalıyor. Sadece ileriye dönük FD/FAVÖK satırında, rehberliğin "
        "üst ucu ve Tenaris'in çarpanı birleşince aralık bugünkü fiyata uzanıyor. Yani piyasa bugünden iyimser senaryoyu fiyatlıyor. Bu bir tavsiye değil; "
        "raporun cevaplaması gereken sorunun görsel hali. Dar grubun şimdilik iki şirket olduğunu da unutma, aralık Jindal SAW gibi isimlerle güncellenecek.",
        "**Reading:** on every trailing multiple, today's market value sits above the peer range. Only on forward EV/EBITDA, where the top of guidance meets "
        "Tenaris's multiple, does the range reach today's price. In other words the market is already pricing the optimistic scenario. This is not a "
        "recommendation; it is the question the report has to answer, drawn as a chart. The narrow group has only two companies for now, and the ranges "
        "will be updated with names such as Jindal SAW.")))

    st.markdown("#### " + L("Duyarlılık: çarpan x 2026 FAVÖK, bugünkü fiyata göre fark", "Sensitivity: multiple x 2026 EBITDA, difference versus today's price"))
    ebitda_grid = [E26_LO + (E26_HI - E26_LO) * i / 4 for i in range(5)]
    mult_grid = [5, 6, 7, 8, 9, 10, 11, 12]
    cells = []
    for m in mult_grid:
        for e in ebitda_grid:
            up = v.upside(v.equity_from_ev_multiple(m, e, ND), MCAP)
            cells.append({"carpan": f"{m}x", "favok": num(e, 0), "up": up * 100, "lbl": pct(up, 0, sign=True)})
    hm = pd.DataFrame(cells)
    x_sort, y_sort = [num(e, 0) for e in ebitda_grid], [f"{m}x" for m in reversed(mult_grid)]
    heat = alt.Chart(hm).mark_rect(cornerRadius=4).encode(
        x=alt.X("favok:O", title=L("2026T FAVÖK (mn $), rehberlik aralığı", "2026E EBITDA ($m), guidance range"), sort=x_sort),
        y=alt.Y("carpan:O", title=L("FD/FAVÖK çarpanı", "EV/EBITDA multiple"), sort=y_sort),
        color=alt.Color("up:Q", scale=alt.Scale(domain=[-60, 0, 60], range=[RED, "#FFF6FA", GREEN], clamp=True, interpolate="rgb"), legend=None),
        tooltip=[alt.Tooltip("carpan:N", title=L("Çarpan", "Multiple")), alt.Tooltip("favok:N", title=L("FAVÖK", "EBITDA")), alt.Tooltip("lbl:N", title=L("Fark", "Difference"))],
    )
    heat_txt = alt.Chart(hm).mark_text(fontSize=12, fontWeight="bold", color=PLUM).encode(
        x=alt.X("favok:O", sort=x_sort), y=alt.Y("carpan:O", sort=y_sort), text="lbl:N")
    st.altair_chart((heat + heat_txt).properties(height=330), width="stretch")
    st.caption(L(
        f"Bugünkü fiyatın ima ettiği 2026T FD/FAVÖK: rehberliğin alt ucunda {num(EV / E26_LO)}x, ortasında {num(EV / E26_MID)}x, üst ucunda {num(EV / E26_HI)}x. "
        f"Karşılaştırma: {NARROW[0]['name']} {num(PEER_FWD[0])}x, {NARROW[1]['name']} {num(PEER_FWD[1])}x (ileriye dönük, EquityRT).",
        f"The 2026E EV/EBITDA implied by today's price: {num(EV / E26_LO)}x at the bottom of guidance, {num(EV / E26_MID)}x at the midpoint, {num(EV / E26_HI)}x at the top. "
        f"For comparison: {NARROW[0]['name']} {num(PEER_FWD[0])}x, {NARROW[1]['name']} {num(PEER_FWD[1])}x (forward, EquityRT)."))

    st.markdown("#### " + L("Makro şok simülatörü: çelik fiyatı, kur ve hacim FAVÖK'ü nasıl etkiler?", "Macro shock simulator: how do steel prices, FX and volume move EBITDA?"))
    IMPLIED_MULT = EV / E26_MID
    st.caption(md(L(
        f"Baz: 2026 rehberliğinin ortası, gelir {money(REV_MID, 0)} ve FAVÖK {money(E26_MID, 0)}. Değer etkisi bugünkü fiyatın ima ettiği {num(IMPLIED_MULT)}x "
        "çarpanla hesaplanıyor. Maliyet yapısı girdileri şirket verisi değil varsayım; faaliyet raporundaki maliyet kırılımıyla güncellenmeli.",
        f"Base: midpoint of 2026 guidance, revenue {money(REV_MID, 0)} and EBITDA {money(E26_MID, 0)}. Value impact uses the {num(IMPLIED_MULT)}x multiple implied "
        "by today's price. Cost structure inputs are assumptions, not company data; they should be updated with the cost breakdown in the annual report.")))
    ASSUMP = L("Varsayım", "Assumption")
    a1, a2, a3, a4 = st.columns(4)
    steel_share = a1.number_input(L("Girdi çeliğin gelire oranı (%)", "Input steel as % of revenue"), 20.0, 90.0, 60.0, step=5.0, help=ASSUMP)
    pass_thru = a2.number_input(L("Fiyat geçişkenliği (%)", "Price pass through (%)"), 0.0, 100.0, 70.0, step=5.0,
                                help=L("Çelik maliyet değişiminin ne kadarı satış fiyatına yansıyor. Varsayım.", "How much of a steel cost change reaches selling prices. Assumption."))
    tl_share = a3.number_input(L("TL cinsi maliyetlerin gelire oranı (%)", "TRY costs as % of revenue"), 0.0, 50.0, 15.0, step=1.0, help=ASSUMP)
    contrib = a4.number_input(L("Hacimde katkı marjı (%)", "Contribution margin on volume (%)"), 0.0, 50.0, 20.0, step=1.0,
                              help=L("Ek bir ton satışın FAVÖK'e kattığı pay. Varsayım.", "The share of an extra ton's revenue that reaches EBITDA. Assumption."))
    b1, b2, b3 = st.columns(3)
    steel_chg = b1.slider(L("Çelik fiyatı değişimi (%)", "Steel price change (%)"), -30, 30, -10)
    fx_chg = b2.slider(L("TL reel değerlenmesi (%)", "Real TRY appreciation (%)"), -20, 20, 10, help=L(
        "Artı değer: TL, enflasyon farkına göre dolar karşısında reel değer kazanıyor, yani kur makası açılıyor; TL maliyetler dolar bazında şişer.",
        "Positive: the lira gains in real terms against the dollar after inflation, so the FX gap widens and TRY costs inflate in dollar terms."))
    vol_chg = b3.slider(L("Satış hacmi değişimi (%)", "Sales volume change (%)"), -20, 20, 0)

    def shock(steel: float, fx: float, vol: float) -> tuple:
        d_steel = -REV_MID * steel_share / 100 * steel / 100 * (1 - pass_thru / 100)
        d_fx = -REV_MID * tl_share / 100 * fx / 100
        d_vol = REV_MID * vol / 100 * contrib / 100
        return d_steel, d_fx, d_vol

    ds, dfx, dv = shock(steel_chg, fx_chg, vol_chg)
    new_e = E26_MID + ds + dfx + dv
    new_rev = REV_MID * (1 + vol_chg / 100) + REV_MID * steel_share / 100 * steel_chg / 100 * pass_thru / 100
    s1, s2, s3, s4 = st.columns(4)
    s1.metric(L("Yeni 2026T FAVÖK (mn $)", "New 2026E EBITDA ($m)"), num(new_e), delta=num(new_e - E26_MID))
    s2.metric(L("Yeni FAVÖK marjı", "New EBITDA margin"), pct(new_e / new_rev), delta=f"{num((new_e / new_rev - M_MID) * 100)} {L('puan', 'pts')}")
    s3.metric(L("Özsermaye etkisi (mn $)", "Equity impact ($m)"), num((new_e - E26_MID) * IMPLIED_MULT, 0),
              delta=pct((new_e - E26_MID) * IMPLIED_MULT / MCAP, 1, sign=True))
    s4.metric(L("Çelik / kur / hacim (mn $)", "Steel / FX / volume ($m)"), f"{num(ds, 0)} / {num(dfx, 0)} / {num(dv, 0)}")

    NEG, POS = L("Olumsuz", "Negative"), L("Olumlu", "Positive")
    tor = []
    for name, lo_d, hi_d in [
        (L("Çelik fiyatı ±%10", "Steel price ±10%"), sum(shock(10, 0, 0)), sum(shock(-10, 0, 0))),
        (L("TL reel kur ±%10", "Real TRY ±10%"), sum(shock(0, 10, 0)), sum(shock(0, -10, 0))),
        (L("Satış hacmi ±%10", "Sales volume ±10%"), sum(shock(0, 0, -10)), sum(shock(0, 0, 10))),
        (L("FAVÖK marjı ±1 puan", "EBITDA margin ±1 pt"), -REV_MID * 0.01, REV_MID * 0.01),
    ]:
        tor.append({"surucu": name, "x": 0, "x2": lo_d * IMPLIED_MULT, "yon": NEG})
        tor.append({"surucu": name, "x": 0, "x2": hi_d * IMPLIED_MULT, "yon": POS})
    mult_name = L("FD/FAVÖK çarpanı ±1x", "EV/EBITDA multiple ±1x")
    tor += [{"surucu": mult_name, "x": 0, "x2": -E26_MID, "yon": NEG}, {"surucu": mult_name, "x": 0, "x2": E26_MID, "yon": POS}]
    tdf = pd.DataFrame(tor)
    tdf["lbl"] = tdf["x2"].map(lambda z: f"{'+' if z > 0 else ''}{num(z, 0)}")
    order = tdf.assign(a=tdf["x2"].abs()).groupby("surucu")["a"].max().sort_values(ascending=False).index.tolist()
    tbars = alt.Chart(tdf).mark_bar(size=22, cornerRadius=4).encode(
        y=alt.Y("surucu:N", sort=order, title=None, axis=alt.Axis(labelLimit=220)),
        x=alt.X("x:Q", title=L("Özsermaye değerine etkisi (mn $)", "Impact on equity value ($m)"), axis=NUM_AXIS), x2="x2:Q",
        color=alt.Color("yon:N", scale=alt.Scale(domain=[NEG, POS], range=[RED, GREEN]), legend=alt.Legend(orient="bottom", title=None)),
        tooltip=["surucu:N", "lbl:N"],
    )
    tt_base = alt.Chart(tdf).encode(y=alt.Y("surucu:N", sort=order), x="x2:Q", text="lbl:N")
    ttxt = (tt_base.mark_text(fontSize=11, color=PLUM, align="left", dx=4).transform_filter("datum.x2 > 0")
            + tt_base.mark_text(fontSize=11, color=PLUM, align="right", dx=-4).transform_filter("datum.x2 <= 0"))
    st.altair_chart((tbars + ttxt).properties(height=250, title=L(
        "Tornado: her sürücü tek başına oynatılınca değer ne kadar değişir?", "Tornado: how much does value move when each driver is shifted on its own?")), width="stretch")
    st.caption(L("Tornado, jürinin resmi soru havuzundaki 'değerlemenizi en çok hangi duyarlılık değiştirir?' sorusunun görsel cevabı.",
                 "The tornado is the visual answer to the official judge question: what sensitivities could significantly alter your valuation?"))

    st.markdown("#### " + L("Senaryolar: ayı, baz, boğa", "Scenarios: bear, base, bull"))
    st.caption(L("Varsayılanlar rehberliğin uçları ve dar peer grubunun ileriye dönük çarpanlarıdır. Hücreleri değiştirip kendi senaryonu savunabilirsin.",
                 "Defaults are the ends of guidance and the forward multiples of the narrow peer group. Edit the cells to defend your own scenario."))
    C_SC, C_REV, C_MAR, C_MUL = L("Senaryo", "Scenario"), L("Gelir (mn $)", "Revenue ($m)"), L("FAVÖK marjı (%)", "EBITDA margin (%)"), L("FD/FAVÖK (x)", "EV/EBITDA (x)")
    scen_default = pd.DataFrame([
        {C_SC: L("Ayı", "Bear"), C_REV: float(REV_LO), C_MAR: M_LO * 100, C_MUL: min(PEER_FWD)},
        {C_SC: L("Baz", "Base"), C_REV: float(REV_MID), C_MAR: M_MID * 100, C_MUL: round(statistics.mean(PEER_FWD), 2)},
        {C_SC: L("Boğa", "Bull"), C_REV: float(REV_HI), C_MAR: M_HI * 100, C_MUL: max(PEER_FWD)},
    ])
    scen = st.data_editor(scen_default, hide_index=True, disabled=[C_SC], key=f"scenario_editor_{LG}", width="stretch")
    scen_out = []
    for _, r in scen.iterrows():
        e = v.guidance_ebitda(r[C_REV], r[C_MAR] / 100)
        eq = v.equity_from_ev_multiple(r[C_MUL], e, ND)
        scen_out.append({C_SC: r[C_SC], L("FAVÖK (mn $)", "EBITDA ($m)"): num(e), L("Özsermaye (mn $)", "Equity ($m)"): num(eq, 0),
                         L("Bugünkü fiyata göre", "vs today's price"): pct(v.upside(eq, MCAP), 1, sign=True)})
    st.dataframe(pd.DataFrame(scen_out), hide_index=True)

    st.markdown("#### " + L("Monte Carlo: 10.000 senaryoda özsermaye değeri dağılımı", "Monte Carlo: equity value distribution across 10,000 scenarios"))
    mc1, mc2, mc3 = st.columns(3)
    rev_rng = mc1.slider(L("2026 gelir aralığı (mn $)", "2026 revenue range ($m)"), 1800, 2800, D_REV, step=50, key="mc_rev")
    mar_rng = mc2.slider(L("FAVÖK marjı aralığı (%)", "EBITDA margin range (%)"), 5.0, 14.0, D_MAR, step=0.5, key="mc_mar")
    mul_rng = mc3.slider(L("FD/FAVÖK çarpan aralığı (x)", "EV/EBITDA multiple range (x)"), 3.0, 16.0, D_MUL, step=0.01, key="mc_mul")
    sims = monte_carlo(tuple(rev_rng), tuple(mar_rng), tuple(mul_rng), ND)
    n = len(sims)
    p5, p50, p95 = sims[int(0.05 * n)], sims[int(0.5 * n)], sims[int(0.95 * n)]
    prob_above = sum(1 for s in sims if s > MCAP) / n
    m1, m2, m3, m4 = st.columns(4)
    m1.metric(L("5. persentil (mn $)", "5th percentile ($m)"), num(p5, 0))
    m2.metric(L("Medyan (mn $)", "Median ($m)"), num(p50, 0), delta=pct(v.upside(p50, MCAP), 1, sign=True))
    m3.metric(L("95. persentil (mn $)", "95th percentile ($m)"), num(p95, 0))
    m4.metric(L("Bugünkü fiyatı aşma olasılığı", "Probability of beating today's price"), pct(prob_above, 1), help=gl_help("monte_carlo"))
    lo_v, hi_v = sims[0], sims[-1]
    width_b = (hi_v - lo_v) / 40 or 1
    counts = [0] * 40
    for s in sims:
        counts[min(int((s - lo_v) / width_b), 39)] += 1
    hist = pd.DataFrame({"x": [lo_v + width_b * (i + 0.5) for i in range(40)], "adet": counts})
    hist_chart = alt.Chart(hist).mark_bar(color=ROSE, cornerRadiusTopLeft=3, cornerRadiusTopRight=3).encode(
        x=alt.X("x:Q", title=L("Özsermaye değeri (mn $)", "Equity value ($m)"), axis=NUM_AXIS), y=alt.Y("adet:Q", title=L("Senaryo sayısı", "Number of scenarios")))
    R_NOW, R_MED = L("Bugünkü piyasa değeri", "Market value today"), L("Medyan senaryo", "Median scenario")
    mc_rules = alt.Chart(pd.DataFrame({"x": [MCAP, p50], "c": [R_NOW, R_MED]})).mark_rule(size=2, strokeDash=[6, 4]).encode(
        x="x:Q", color=alt.Color("c:N", scale=alt.Scale(domain=[R_NOW, R_MED], range=[PLUM, PINK]), legend=alt.Legend(orient="bottom", title=None)))
    st.altair_chart((hist_chart + mc_rules).properties(height=260), width="stretch")
    st.caption(L(
        "Her değişken kendi aralığında eşit olasılıkla çekiliyor; sabit tohum (42) sayesinde sonuç her açılışta aynı ve tekrarlanabilir. "
        "Aralıklar veri değil varsayım: varsayılanlar şirket rehberliği ve dar peer çarpanları.",
        "Each variable is drawn with equal probability within its range; a fixed seed (42) makes the result identical and reproducible on every load. "
        "The ranges are assumptions, not data: defaults are company guidance and narrow peer multiples."))

    st.markdown("#### " + L("Reverse DCF: bugünkü fiyat hangi nakit akışını fiyatlıyor?", "Reverse DCF: what cash flow does today's price imply?"))
    r1, r2 = st.columns(2)
    wacc = r1.slider(L("WACC, USD bazında (%)", "WACC, USD based (%)"), 7.0, 15.0, D_W, step=0.25, key="rd_wacc",
                     help=L("Varsayım, veri değil. Kendi WACC hesabınla değiştir.", "Assumption, not data. Replace it with your own WACC build."))
    g_term = r2.slider(L("Sonsuz büyüme (%)", "Terminal growth (%)"), 0.0, 4.0, D_G, step=0.25, key="rd_g", help=L("Varsayım, veri değil.", "Assumption, not data."))
    fcff = v.implied_steady_fcff(EV, wacc / 100, g_term / 100)
    k1, k2, k3 = st.columns(3)
    k1.metric(L("İma edilen kalıcı SNA (mn $/yıl)", "Implied permanent FCF ($m/yr)"), num(fcff), help=gl_help("reverse_dcf"))
    k2.metric(L("Son 12 ay FAVÖK'e oranı", "As % of TTM EBITDA"), pct(fcff / TTM_EBITDA, 0))
    k3.metric(L("2026T FAVÖK ortasına oranı", "As % of 2026E EBITDA midpoint"), pct(fcff / E26_MID, 0))
    st.info(md(L(
        f"**Okuma:** WACC {pp(wacc, 2)} ve büyüme {pp(g_term, 2)} ile piyasa, her yıl yaklaşık {money(fcff, 0)} serbest nakit akımının sonsuza kadar süreceğini "
        f"fiyatlıyor. Bu, rehberliğin ortasındaki FAVÖK'ün {pct(fcff / E26_MID, 0)}'i. Kıyas için 1Y26 serbest nakit akımı {money(CF['serbest_nakit_akimi'], 0)} idi, "
        f"ama {money(CF['isletme_sermayesi'], 0)}'ı işletme sermayesinden geldi. Yatırım yoğun bir işte bu dönüşüm oranı makul mü? Jüriye bu soruyla gitmek güçlü bir hamle.",
        f"**Reading:** at a WACC of {pp(wacc, 2)} and growth of {pp(g_term, 2)}, the market is pricing about {money(fcff, 0)} of free cash flow every year, forever. "
        f"That is {pct(fcff / E26_MID, 0)} of EBITDA at the guidance midpoint. For comparison, 1H26 free cash flow was {money(CF['serbest_nakit_akimi'], 0)}, but "
        f"{money(CF['isletme_sermayesi'], 0)} of it came from working capital. Is that conversion rate reasonable in a capital intensive business? Taking this "
        "question to the judges is a strong move.")))
    W_GRID, G_GRID = [8, 9, 10, 11, 12, 13, 14], [1.0, 1.5, 2.0, 2.5, 3.0, 3.5]
    rhm = pd.DataFrame([
        {"wacc": pp(w, 0), "g": pp(gg), "oran": v.implied_steady_fcff(EV, w / 100, gg / 100) / E26_MID * 100,
         "lbl": pct(v.implied_steady_fcff(EV, w / 100, gg / 100) / E26_MID, 0)}
        for w in W_GRID for gg in G_GRID
    ])
    gx, wy = [pp(x) for x in G_GRID], [pp(w, 0) for w in W_GRID]
    rheat = alt.Chart(rhm).mark_rect(cornerRadius=4).encode(
        x=alt.X("g:O", title=L("Sonsuz büyüme", "Terminal growth"), sort=gx), y=alt.Y("wacc:O", title="WACC", sort=wy),
        color=alt.Color("oran:Q", scale=alt.Scale(range=["#F6E4F2", "#7B3F6E"], interpolate="rgb"), legend=None))
    rtxt = alt.Chart(rhm).mark_text(fontSize=12, fontWeight="bold").encode(
        x=alt.X("g:O", sort=gx), y=alt.Y("wacc:O", sort=wy), text="lbl:N",
        color=alt.condition("datum.oran > 70", alt.value("white"), alt.value(PLUM)))
    st.altair_chart((rheat + rtxt).properties(height=300, title=L(
        "Gereken nakit dönüşümü: ima edilen serbest nakit akımı / 2026T FAVÖK", "Required cash conversion: implied free cash flow / 2026E EBITDA")), width="stretch")

    st.markdown("#### 🔗 " + L("Bu senaryoyu takımla paylaş", "Share this scenario with the team"))
    share_params = {"w": wacc, "g": g_term, "rlo": rev_rng[0], "rhi": rev_rng[1], "mlo": mar_rng[0], "mhi": mar_rng[1],
                    "xlo": round(mul_rng[0], 2), "xhi": round(mul_rng[1], 2), "lang": LG}
    share_url = f"{APP_URL}?{urlencode(share_params)}"
    st.caption(L("Link, Monte Carlo ve reverse DCF ayarlarını taşır. Takım arkadaşın açınca aynı varsayımlarla aynı grafikleri görür.",
                 "The link carries the Monte Carlo and reverse DCF settings. When a teammate opens it, they see the same charts with the same assumptions."))
    st.code(share_url, language=None)
    sh1, sh2 = st.columns([3, 1])
    scen_name = sh1.text_input(L("Senaryo adı", "Scenario name"), placeholder=L("Örn. Temkinli marj", "e.g. Cautious margin"), key="scen_name")
    sh2.write("")
    if sh2.button(L("Takım kütüphanesine kaydet", "Save to team library")):
        if not ME:
            st.warning(L("Önce Takım Masası sekmesinde adını yaz.", "Enter your name on the Team Desk tab first."))
        else:
            summary = f"WACC {pp(wacc, 2)}, g {pp(g_term, 2)}, {L('medyan', 'median')} {money(p50, 0)}, P(>{L('bugün', 'today')}) {pct(prob_above, 0)}"
            get_board().save_scenario(scen_name or L("Adsız senaryo", "Untitled scenario"), ME, share_url, summary)
            st.success(L("Kaydedildi; Takım Masası'nda görünüyor.", "Saved; it now appears on the Team Desk."))

# 3. FİNANSAL ANALİZ
with tabs[2]:
    h1, h2 = P["1Y25"], P["1Y26"]
    f1, f2, f3, f4 = st.columns(4)
    f1.metric(L("1Y26 gelir (mn $)", "1H26 revenue ($m)"), num(h2["gelir"]), delta=pct(v.growth(h2["gelir"], h1["gelir"]), 1, sign=True))
    f2.metric(L("1Y26 FAVÖK (mn $)", "1H26 EBITDA ($m)"), num(h2["favok"]), delta=pct(v.growth(h2["favok"], h1["favok"]), 1, sign=True))
    f3.metric(L("1Y26 FAVÖK marjı", "1H26 EBITDA margin"), pct(h2["favok"] / h2["gelir"]),
              delta=f"{num((h2['favok'] / h2['gelir'] - h1['favok'] / h1['gelir']) * 100)} {L('puan', 'pts')}")
    f4.metric(L("1Y26 net kâr (mn $)", "1H26 net profit ($m)"), num(h2["net_kar"]), delta=pct(v.growth(h2["net_kar"], h1["net_kar"]), 0, sign=True))

    q_keys = [k for k, d in P.items() if d["tur"] == "ceyrek"]
    q_lbls = [period(k) for k in q_keys]
    qdf = pd.DataFrame([{"donem": period(k), "gelir": P[k]["gelir"], "marj": P[k]["favok"] / P[k]["gelir"] * 100} for k in q_keys])
    qbase = alt.Chart(qdf).encode(x=alt.X("donem:N", sort=q_lbls, title=None))
    qbars = qbase.mark_bar(color=LAV, size=46, cornerRadiusTopLeft=6, cornerRadiusTopRight=6).encode(y=alt.Y("gelir:Q", title=L("Gelir (mn $)", "Revenue ($m)")))
    qline = qbase.mark_line(color=PINK, strokeWidth=3, point=alt.OverlayMarkDef(size=90, color=PINK)).encode(
        y=alt.Y("marj:Q", title=L("FAVÖK marjı (%)", "EBITDA margin (%)"), scale=alt.Scale(domain=[0, 14])))
    qtxt = qbase.mark_text(dy=-14, color=PINK, fontWeight="bold").encode(
        y=alt.Y("marj:Q", scale=alt.Scale(domain=[0, 14]), axis=None), text=alt.Text("marj:Q", format=".1f"))
    cA, cB = st.columns(2)
    with cA:
        st.markdown("##### " + L("Çeyreklik gelir ve FAVÖK marjı", "Quarterly revenue and EBITDA margin"))
        st.altair_chart(alt.layer(qbars, qline + qtxt).resolve_scale(y="independent").properties(height=280), width="stretch")
    with cB:
        st.markdown("##### " + L("Kaldıraç: net borç / son 12 ay FAVÖK", "Leverage: net debt / TTM EBITDA"))
        l_lbls = [period(k) for k in LEV]
        ldf = pd.DataFrame([{"donem": period(k), "x": val} for k, val in LEV.items()])
        lbar = alt.Chart(ldf).mark_bar(color=PINK, size=46, cornerRadiusTopLeft=6, cornerRadiusTopRight=6).encode(
            x=alt.X("donem:N", sort=l_lbls, title=None), y=alt.Y("x:Q", title=L("Net borç / FAVÖK (x)", "Net debt / EBITDA (x)")))
        ltxt = lbar.mark_text(dy=-10, color=PLUM, fontWeight="bold").encode(text=alt.Text("x:Q", format=".1f"))
        st.altair_chart((lbar + ltxt).properties(height=280), width="stretch")
        st.caption(f"{L('Kaynak', 'Source')}: {FIN['kaldirac_serisi']['kaynak']}")

    cC, cD = st.columns(2)
    with cC:
        st.markdown("##### " + L("Yıllık gelir ve 2026 rehberliği", "Annual revenue and 2026 guidance"))
        T_LBL, E_LBL = L("Son 12 ay", "TTM"), L("2026T", "2026E")
        adf = pd.DataFrame([
            {"donem": "2024", "gelir": P["2024"]["gelir"], "lo": None, "hi": None},
            {"donem": "2025", "gelir": P["2025"]["gelir"], "lo": None, "hi": None},
            {"donem": T_LBL, "gelir": TTM_REV, "lo": None, "hi": None},
            {"donem": E_LBL, "gelir": REV_MID, "lo": REV_LO, "hi": REV_HI},
        ])
        a_sort = list(adf["donem"])
        abars = alt.Chart(adf).mark_bar(size=46, cornerRadiusTopLeft=6, cornerRadiusTopRight=6).encode(
            x=alt.X("donem:N", sort=a_sort, title=None), y=alt.Y("gelir:Q", title=L("Gelir (mn $)", "Revenue ($m)")),
            color=alt.condition(f"datum.donem == '{E_LBL}'", alt.value(ROSE), alt.value(LAV)))
        aerr = alt.Chart(adf.dropna()).mark_rule(color=PLUM, size=3).encode(x=alt.X("donem:N", sort=a_sort), y="lo:Q", y2="hi:Q")
        st.altair_chart((abars + aerr).properties(height=260), width="stretch")
    with cD:
        st.markdown("##### " + L("1Y26 segment dağılımı ve yıllık değişim", "1H26 segment mix and year on year change"))
        sdf = pd.DataFrame(SEG["items"])
        sdf["lbl"] = sdf.apply(lambda r: f"{pp(r['pay'], 0)} {L('pay', 'share')} · {pct(r['yillik_degisim'] / 100, 1, sign=True)}", axis=1)
        sbar = alt.Chart(sdf).mark_bar(size=26, cornerRadiusEnd=6).encode(
            y=alt.Y("segment:N", sort="-x", title=None), x=alt.X("gelir:Q", title=L("Gelir (mn $)", "Revenue ($m)")),
            color=alt.condition("datum.yillik_degisim > 0", alt.value(PINK), alt.value("#C9B6C4")))
        stxt = sbar.mark_text(align="left", dx=6, color=PLUM, fontSize=11).encode(text="lbl:N")
        st.altair_chart((sbar + stxt).properties(height=260), width="stretch")
        st.caption(f"{L('Kaynak', 'Source')}: {SEG['kaynak']}")

    op_lev_25 = v.growth(P["2025"]["favok"], P["2024"]["favok"]) / v.growth(P["2025"]["gelir"], P["2024"]["gelir"])
    s_infra, s_ind = SEG["items"][0], SEG["items"][2]
    q1m, q2m = P["1Ç26"]["favok"] / P["1Ç26"]["gelir"], P["2Ç26"]["favok"] / P["2Ç26"]["gelir"]
    st.markdown("#### " + L("Analist notları", "Analyst notes"))
    st.markdown(L(
        f"- **Faaliyet kaldıracı çalışıyor.** 2025'te gelir {pct(v.growth(P['2025']['gelir'], P['2024']['gelir']))} artarken FAVÖK "
        f"{pct(v.growth(P['2025']['favok'], P['2024']['favok']))} arttı; FAVÖK gelirden yaklaşık {num(op_lev_25)} kat hızlı büyüdü.\n"
        f"- **Büyümenin motoru tek segment.** {s_infra['segment']} 1Y26'da {pct(s_infra['yillik_degisim'] / 100, 1, sign=True)} büyüyüp gelirin "
        f"{pp(s_infra['pay'], 0)}'ine ulaştı; {s_ind['segment']} ise {pct(s_ind['yillik_degisim'] / 100, 1, sign=True)} geriledi.\n"
        f"- **Marj oynak.** Çeyreklik FAVÖK marjı 1Ç26'da {pct(q1m)}, 2Ç26'da {pct(q2m)}. Hangisinin normal olduğu tezin ta kendisi.\n"
        f"- **Mutabakat.** Piyasa değeri / son 12 ay net kâr = {num(MCAP)} / {num(TTM_NI)} = {num(MCAP / TTM_NI, 2)}; EquityRT Peer Performance ekranındaki "
        f"{num(MKT['p_e'], 2)} ile tutuyor. Snapshot ekranındaki {num(MKT['p_e_snapshot_ekrani'], 2)} farklı bir dönem ya da kur bazı kullanıyor olmalı.",
        f"- **Operating leverage is working.** In 2025 revenue grew {pct(v.growth(P['2025']['gelir'], P['2024']['gelir']))} while EBITDA grew "
        f"{pct(v.growth(P['2025']['favok'], P['2024']['favok']))}; EBITDA grew about {num(op_lev_25)} times faster than revenue.\n"
        f"- **Growth has a single engine.** {s_infra['segment']} grew {pct(s_infra['yillik_degisim'] / 100, 1, sign=True)} in 1H26 to reach "
        f"{pp(s_infra['pay'], 0)} of revenue, while {s_ind['segment']} fell {pct(s_ind['yillik_degisim'] / 100, 1, sign=True)}.\n"
        f"- **The margin is volatile.** Quarterly EBITDA margin was {pct(q1m)} in 1Q26 and {pct(q2m)} in 2Q26. Which one is normal is the thesis itself.\n"
        f"- **Reconciliation.** Market value / TTM net profit = {num(MCAP)} / {num(TTM_NI)} = {num(MCAP / TTM_NI, 2)}, matching the {num(MKT['p_e'], 2)} on "
        f"EquityRT's Peer Performance screen. The {num(MKT['p_e_snapshot_ekrani'], 2)} on the Snapshot screen must use a different period or currency basis."))

    st.markdown("#### " + L("Rasyo panosu: BRSAN ve dar peer grubu", "Ratio dashboard: BRSAN and the narrow peer group"))
    tn, vk = NARROW[0], NARROW[1]
    NA = L("yok", "n/a")

    def xf(val, d=1):
        return NA if val is None else f"{num(val, d)}x"

    def pf(val, d=1):
        return NA if val is None else pp(val, d)

    capex_rev = -CF["yatirim"] / h2["gelir"]
    GRP = {k: L(t, e) for k, t, e in [("val", "Değerleme", "Valuation"), ("prof", "Kârlılık", "Profitability"), ("eff", "Verimlilik", "Efficiency"),
                                      ("bs", "Bilanço", "Balance sheet"), ("cash", "Nakit", "Cash"), ("sh", "Ortaklara", "Shareholders"), ("risk", "Risk", "Risk")]}
    ratio_rows = [
        (GRP["val"], L("FD/FAVÖK son 12 ay", "EV/EBITDA TTM"), xf(EV / TTM_EBITDA), xf(tn["ev_ebitda_ttm"]), xf(vk["ev_ebitda_ttm"]), L("FD / son 12 ay FAVÖK", "EV / TTM EBITDA")),
        (GRP["val"], L("FD/FAVÖK ileriye dönük", "EV/EBITDA forward"), xf(EV / E26_MID), xf(tn["ev_ebitda_forward"]), xf(vk["ev_ebitda_forward"]),
         L("BRSAN: rehberlik ortası; peer'lar: EquityRT konsensüsü", "BRSAN: guidance midpoint; peers: EquityRT consensus")),
        (GRP["val"], L("F/K son 12 ay", "P/E TTM"), xf(MKT["p_e"], 2), xf(tn["p_e_ttm"], 2), xf(vk["p_e_ttm"], 2),
         L("EquityRT; USD son 12 ay net kârla mutabık", "EquityRT; reconciled with USD TTM net profit")),
        (GRP["val"], L("PD/DD", "P/B"), xf(MKT["p_bv"], 2), xf(tn["p_bv"], 2), xf(vk["p_bv"], 2), "EquityRT"),
        (GRP["val"], L("FD/Satış son 12 ay", "EV/Sales TTM"), xf(EV / TTM_REV, 2), NA, NA, L("FD / son 12 ay gelir", "EV / TTM revenue")),
        (GRP["prof"], L("FAVÖK marjı son 12 ay", "EBITDA margin TTM"), pct(TTM_EBITDA / TTM_REV), NA, NA, L("Son 12 ay FAVÖK / gelir", "TTM EBITDA / revenue")),
        (GRP["prof"], L("Net kâr marjı son 12 ay", "Net margin TTM"), pct(TTM_NI / TTM_REV), NA, NA, L("Son 12 ay net kâr / gelir", "TTM net profit / revenue")),
        (GRP["prof"], "ROE", pct(DP["roe"]), pf(tn["roe_pct"]), pf(vk["roe_pct"]), L("Net kâr / özsermaye (PD ÷ PD/DD)", "Net profit / equity (MV ÷ P/B)")),
        (GRP["prof"], "ROA", pct(TTM_NI / TA), pf(tn["roa_pct"]), pf(vk["roa_pct"]), L("Net kâr / toplam aktif (EquityRT)", "Net profit / total assets (EquityRT)")),
        (GRP["eff"], L("Aktif devir hızı", "Asset turnover"), xf(DP["aktif_devir"], 2), NA, NA, L("Son 12 ay gelir / toplam aktif", "TTM revenue / total assets")),
        (GRP["bs"], L("Net borç / FAVÖK", "Net debt / EBITDA"), xf(ND / TTM_EBITDA, 2), xf(tn["net_debt_ebitda"], 2), xf(vk["net_debt_ebitda"], 2),
         L("Eksi değer net nakit demek", "A negative value means net cash")),
        (GRP["bs"], L("Borç / aktif", "Debt / assets"), NA, pf(tn["debt_asset_pct"]), pf(vk["debt_asset_pct"]),
         L("EquityRT; BRSAN için brüt borç KAP'tan eklenecek", "EquityRT; gross debt for BRSAN to be added from KAP")),
        (GRP["cash"], L("Yatırım harcaması / gelir 1Y26", "Capex / revenue 1H26"), pct(capex_rev), NA, NA, L("2Ç26 sunumu s.22", "2Q26 deck p.22")),
        (GRP["cash"], L("Nakit dönüşümü 1Y26", "Cash conversion 1H26"), pct(CF["serbest_nakit_akimi"] / h2["favok"], 0), NA, NA,
         L("SNA / FAVÖK, işletme sermayesi dahil", "FCF / EBITDA, including working capital")),
        (GRP["sh"], L("Temettü verimi", "Dividend yield"), L("yok (2025 kârı dağıtılmadı)", "none (no 2025 payout)"),
         pf(tn["dividend_yield_ttm_pct"], 2), pf(vk["dividend_yield_ttm_pct"], 2), "EquityRT, KAP"),
        (GRP["risk"], L("Beta (2 yıl)", "Beta (2y)"), NA, num(tn["beta_2y"], 2), num(vk["beta_2y"], 2), "EquityRT"),
    ]
    st.dataframe(pd.DataFrame(ratio_rows, columns=[L("Grup", "Group"), L("Rasyo", "Ratio"), "BRSAN", tn["name"], vk["name"], L("Hesap ve kaynak", "Formula and source")]),
                 hide_index=True)
    st.caption(L(
        "BRSAN özsermayesi piyasa değerinin PD/DD'ye bölünmesiyle, toplam aktif EquityRT Peer Performance ekranından alındı (22.09.2026). "
        "\"yok\" olan hücreler kaynakta bulunmayan verilerdir, tahminle doldurulmadı. Rasyoların ne anlattığı için yukarıdaki ℹ️ rehberine bak.",
        "BRSAN equity is market value divided by P/B; total assets come from EquityRT's Peer Performance screen (22.09.2026). Cells marked \"n/a\" are "
        "not in the sources and were not filled with guesses. See the ℹ️ guide above for what each ratio means."))

    tn_lev, vk_lev = tn["roe_pct"] / tn["roa_pct"], vk["roe_pct"] / vk["roa_pct"]
    raw('<div class="sac-thesis"><b>DuPont:</b> ' + L(
        f"ROE {pct(DP['roe'])} = net marj {pct(DP['net_marj'])} × aktif devir hızı {num(DP['aktif_devir'], 2)}x × finansal kaldıraç {num(DP['kaldirac'], 2)}x. "
        f"Karşılaştırma: Tenaris ROE {pp(tn['roe_pct'])}, Vallourec {pp(vk['roe_pct'])}. BRSAN'ın finansal kaldıracı, Tenaris'in yaklaşık {num(tn_lev, 2)}x ve "
        f"Vallourec'in yaklaşık {num(vk_lev, 2)}x seviyesinin (ROE ÷ ROA) üstünde. Yani ROE'yi borçla büyütme alanı yok; ROE'yi taşıyacak asıl kaldıraç net marj. "
        "Bu da tezin sorusuyla aynı yere çıkıyor: marj kalıcı mı?",
        f"ROE {pct(DP['roe'])} = net margin {pct(DP['net_marj'])} × asset turnover {num(DP['aktif_devir'], 2)}x × financial leverage {num(DP['kaldirac'], 2)}x. "
        f"For comparison: Tenaris ROE {pp(tn['roe_pct'])}, Vallourec {pp(vk['roe_pct'])}. BRSAN's financial leverage is above Tenaris at about {num(tn_lev, 2)}x and "
        f"Vallourec at about {num(vk_lev, 2)}x (ROE ÷ ROA). There is no room to grow ROE with debt; the lever that has to carry it is net margin, "
        "which leads back to the thesis question: is the margin durable?") + "</div>")

    st.markdown("#### " + L("Sermaye dağılımı: nakit nereye gitti? (1Y26)", "Capital allocation: where did the cash go? (1H26)"))
    K_CASH, K_IN, K_OUT = L("Kasa", "Cash"), L("Giriş", "Inflow"), L("Çıkış", "Outflow")
    steps = [
        (L("2025 sonu kasa", "Cash end 2025"), CF["kasa_2025"], K_CASH),
        (L("Faaliyetlerden", "From operations"), CF["faaliyet_nakdi"], K_IN),
        (L("Yatırım", "Investing"), CF["yatirim_nakit_cikisi"], K_OUT),
        (L("Finansman", "Financing"), CF["finansman_nakit_cikisi"], K_OUT),
        (L("2Ç26 sonu kasa", "Cash end 2Q26"), CF["kasa_2c26"], K_CASH),
    ]
    wf, run = [], 0.0
    for name, val, kind in steps:
        if kind == K_CASH:
            wf.append({"adim": name, "y": 0, "y2": val, "tur": kind, "lbl": num(val, 0)})
            run = val
        else:
            wf.append({"adim": name, "y": run, "y2": run + val, "tur": kind, "lbl": f"{'+' if val > 0 else ''}{num(val, 0)}"})
            run += val
    wdf = pd.DataFrame(wf)
    w_sort = [s[0] for s in steps]
    wbars = alt.Chart(wdf).mark_bar(size=54, cornerRadius=4).encode(
        x=alt.X("adim:N", sort=w_sort, title=None, axis=alt.Axis(labelAngle=0)), y=alt.Y("y:Q", title=L("mn $", "$m")), y2="y2:Q",
        color=alt.Color("tur:N", scale=alt.Scale(domain=[K_CASH, K_IN, K_OUT], range=[LAV, GREEN, RED]), legend=alt.Legend(orient="bottom", title=None)))
    wtxt = alt.Chart(wdf).mark_text(dy=-8, color=PLUM, fontWeight="bold").encode(x=alt.X("adim:N", sort=w_sort), y=alt.Y("y2:Q"), text="lbl:N")
    wc1, wc2 = st.columns([3, 2])
    wc1.altair_chart((wbars + wtxt).properties(height=280), width="stretch")
    wc2.markdown(md(L(
        f"- Faaliyetlerden {money(CF['faaliyet_nakdi'], 0)} nakit girdi, {money(-CF['yatirim_nakit_cikisi'], 0)}'ı yatırıma gitti; yatırım harcaması gelirin {pct(capex_rev)}'ü.\n"
        f"- Net borç bir yılda {money(P['2Ç25']['net_borc'], 0)}'dan {money(ND, 0)}'a indi, kasa {money(CF['kasa_2c26'], 0)}'a çıktı.\n"
        "- Ortaklara dağıtım yok: 2025 kârı dağıtılmadı (yasal kayıtlarda TMS 29 kaynaklı zarar).\n"
        "- **Okuma:** Sermaye önce bilançoya ve büyüme yatırımına gidiyor. Jürinin soracağı soru: bu yatırımın getirisi (ROIC) sermaye maliyetini aşıyor mu? "
        "Yatırılan sermaye KAP bilançosundan eklenince ROIC ile WACC yan yana konacak.",
        f"- {money(CF['faaliyet_nakdi'], 0)} of cash came in from operations and {money(-CF['yatirim_nakit_cikisi'], 0)} went to investment; capex was {pct(capex_rev)} of revenue.\n"
        f"- Net debt fell from {money(P['2Ç25']['net_borc'], 0)} to {money(ND, 0)} in a year, and cash rose to {money(CF['kasa_2c26'], 0)}.\n"
        "- No distribution to shareholders: the 2025 profit was not paid out (a TAS 29 driven loss in the statutory books).\n"
        "- **Reading:** capital goes to the balance sheet and growth investment first. The question judges will ask: does the return on that investment (ROIC) "
        "exceed the cost of capital? Once invested capital is added from the KAP balance sheet, ROIC and WACC will sit side by side.")))
    st.caption(f"{L('Kaynak', 'Source')}: {CF['kaynak']}. {CF['not']}")

    st.markdown("##### " + L("Kaynak tablo", "Source table"))
    tbl = pd.DataFrame([
        {L("Dönem", "Period"): period(k), L("Gelir", "Revenue"): num(d["gelir"]), L("FAVÖK", "EBITDA"): num(d["favok"]),
         L("FAVÖK marjı", "EBITDA margin"): pct(d["favok"] / d["gelir"]), L("Net kâr", "Net profit"): num(d["net_kar"]),
         L("Net borç", "Net debt"): num(d["net_borc"], 0) if "net_borc" in d else ""}
        for k, d in P.items()
    ])
    st.dataframe(tbl, hide_index=True)
    st.caption(f"{L('Kaynak', 'Source')}: {FIN['kaynak']}. [{SRC['d1c26']['ad']}]({SRC['d1c26']['url']}) · [{SRC['d2c26']['ad']}]({SRC['d2c26']['url']}). " + L(
        "Yüzdeler yuvarlanmış sunum rakamlarından hesaplandı; sunumdaki yüzdelerle ondalıkta fark olabilir.",
        "Percentages are calculated from rounded deck figures and may differ from the deck in the decimal."))

# 4. RİSK MATRİSİ
with tabs[3]:
    st.caption(L(
        "Olasılık ve etki puanları veri değil, analist yargısıdır (1 düşük, 5 yüksek). Jüride savunabileceğin şekilde tablodan değiştir; grafik anında "
        "güncellenir. Kazanan raporlarda her riskin yanında bir azaltıcı durur, burada da öyle.",
        "Probability and impact scores are analyst judgement, not data (1 low, 5 high). Change them in the table the way you would defend them to the judges; "
        "the chart updates instantly. Winning reports pair every risk with a mitigant, and so does this one."))
    C_R, C_P, C_I, C_S = L("Risk", "Risk"), L("Olasılık", "Probability"), L("Etki", "Impact"), L("Skor", "Score")
    rdf0 = pd.DataFrame([{C_R: r["risk"], C_P: r["olasilik"], C_I: r["etki"]} for r in PITCH["risks"]])
    rdf = st.data_editor(rdf0, hide_index=True, disabled=[C_R], key=f"risk_editor_{LG}", width="stretch", column_config={
        C_P: st.column_config.NumberColumn(min_value=1, max_value=5, step=1), C_I: st.column_config.NumberColumn(min_value=1, max_value=5, step=1)})
    plot = rdf.copy()
    plot[C_S] = plot[C_P] * plot[C_I]
    offsets = [(0, 0), (0.22, -0.24), (-0.22, 0.24), (0.22, 0.24), (-0.22, -0.24)]
    seen: dict = {}
    xs, ys = [], []
    for _, r in plot.iterrows():
        key = (r[C_P], r[C_I])
        k = seen.get(key, 0)
        seen[key] = k + 1
        dx_, dy_ = offsets[k % len(offsets)]
        xs.append(r[C_P] + dx_)
        ys.append(r[C_I] + dy_)
    plot["x"], plot["y"], plot["name"], plot["score"] = xs, ys, plot[C_R], plot[C_S]
    zone = alt.Chart(pd.DataFrame([{"x": 0.5, "x2": 5.5, "y": 0.5, "y2": 5.5}])).mark_rect(color="#FFF8FB", stroke="#F0D5E6").encode(x="x:Q", x2="x2:Q", y="y:Q", y2="y2:Q")
    diag = alt.Chart(pd.DataFrame({"x": [0.5, 5.5], "y": [5.5, 0.5]})).mark_line(color="#F0D5E6", strokeDash=[4, 4]).encode(x="x:Q", y="y:Q")
    dots = alt.Chart(plot[["x", "y", "name", "score"]]).mark_circle(opacity=0.9, stroke="white", strokeWidth=2).encode(
        x=alt.X("x:Q", title=C_P, scale=alt.Scale(domain=[0.5, 5.5]), axis=alt.Axis(values=[1, 2, 3, 4, 5])),
        y=alt.Y("y:Q", title=C_I, scale=alt.Scale(domain=[0.5, 5.5]), axis=alt.Axis(values=[1, 2, 3, 4, 5])),
        size=alt.Size("score:Q", scale=alt.Scale(range=[300, 1400]), legend=None),
        color=alt.Color("score:Q", scale=alt.Scale(domain=[1, 25], range=["#E7C9DD", "#B23A48"]), legend=None),
        tooltip=[alt.Tooltip("name:N", title=C_R), alt.Tooltip("score:Q", title=C_S)])
    dtxt = alt.Chart(plot[["x", "y", "name"]]).mark_text(align="left", dx=16, fontSize=11, color=PLUM).encode(x="x:Q", y="y:Q", text="name:N")
    st.altair_chart((zone + diag + dots + dtxt).properties(height=420), width="stretch")
    by_name = {r["risk"]: r for r in PITCH["risks"]}
    for _, r in plot.sort_values(C_S, ascending=False).iterrows():
        info = by_name[r[C_R]]
        with st.expander(f"{r[C_R]} · {L('skor', 'score')} {int(r[C_S])}"):
            st.markdown(md(f"**{L('Kanıt', 'Evidence')}:** {info['kanit']}\n\n**{L('Azaltıcı', 'Mitigant')}:** {info['azaltici']}"))

# 5. ESG
with tabs[4]:
    E = PITCH["esg"]
    raw(f'<div class="sac-thesis"><b>{L("ESG tezimiz:", "Our ESG thesis:")}</b> {E["ozet"]}</div>')
    labels_esg = {"E": L("Çevresel", "Environmental"), "S": L("Sosyal", "Social"), "G": L("Kurumsal yönetim", "Governance")}
    for col, key in zip(st.columns(3), ["E", "S", "G"]):
        with col:
            st.markdown(f"##### {labels_esg[key]}")
            for item in [i for i in E["dogrulanmis"] if i["alan"] == key]:
                src = f'<a href="{item["url"]}" target="_blank">{item["kaynak"]}</a>' if item.get("url") else item["kaynak"]
                raw(f'<div class="sac-card"><p>{item["bilgi"]}</p><div class="sac-src">{L("Kaynak", "Source")}: {src}</div></div>')

    st.markdown("#### " + L("SASB önemlilik haritası ve değerlemeye bağlantı", "SASB materiality map and link to valuation"))
    st.caption(L("Konular SASB / IFRS S2 Iron & Steel Producers sektör rehberinden; kanıt sütunu kamuya açık verinin bugünkü durumunu gösteriyor.",
                 "Topics come from the SASB / IFRS S2 Iron & Steel Producers industry guide; the evidence column shows the current state of public data."))
    C_EV = L("Kanıt", "Evidence")
    sasb = pd.DataFrame(E["sasb"]).rename(columns={
        "konu": L("Konu", "Topic"), "neden": L("Neden önemli", "Why it matters"), "borusan": L("Borusan'da durum", "Status at Borusan"),
        "degerleme": L("Değerlemeye etkisi", "Valuation impact"), "kanit": C_EV})
    st.dataframe(sasb, hide_index=True)
    ev_counts = sasb[C_EV].value_counts().to_dict()
    n_part, n_none = ev_counts.get(L("Kısmi", "Partial"), 0), ev_counts.get(L("Veri yok", "No data"), 0)
    st.caption(L(
        f"Veri şeffaflığı: {len(sasb)} önemli konu içinde kısmi kanıtlı konu sayısı {n_part}, kamuya açık verisi olmayan konu sayısı {n_none}. "
        "Bu boşluklar TSRS raporunun tam metninden kapatılacak.",
        f"Data transparency: of {len(sasb)} material topics, {n_part} have partial evidence and {n_none} have no public data. "
        "These gaps will be closed from the full text of the TSRS report."))

    st.markdown("#### " + L("ESG maliyetini değerlemeye bağla: karbon maliyeti hesaplayıcı", "Link ESG cost to valuation: carbon cost calculator"))
    st.caption(L(
        "Jürinin resmi soru havuzunda şu soru var: ESG kaynaklı maliyetleri değerlemenize nasıl yansıttınız? Bu hesaplayıcı cevabın iskeleti. "
        "Girdiler varsayım; AB gelir payı rakamı PDF'ten teyit edilmeden rapora girmemeli.",
        "The official judge question pool asks: how did you factor ESG related costs into your valuation? This calculator is the skeleton of the answer. "
        "Inputs are assumptions; the EU revenue share must not go into the report before it is confirmed from the PDF."))
    e1, e2, e3 = st.columns(3)
    eu_share = e1.number_input(L("AB gelir payı (%)", "EU revenue share (%)"), 0.0, 60.0, float(E["ab_gelir_payi"]["deger"]), step=1.0, help=E["ab_gelir_payi"]["not"])
    carbon = e2.number_input(L("Aktarılamayan karbon maliyeti (AB gelirinin %'si)", "Carbon cost not passed on (% of EU revenue)"), 0.0, 15.0, 2.0, step=0.5)
    mult_e = e3.number_input(L("Uygulanan FD/FAVÖK (x)", "Applied EV/EBITDA (x)"), 2.0, 20.0, round(EV / E26_MID, 1), step=0.5,
                             help=L("Varsayılan: bugünkü fiyatın ima ettiği 2026T çarpanı", "Default: the 2026E multiple implied by today's price"))
    hit = REV_MID * eu_share / 100 * carbon / 100
    eq_hit = hit * mult_e
    z1, z2, z3 = st.columns(3)
    z1.metric(L("Yıllık FAVÖK etkisi (mn $)", "Annual EBITDA impact ($m)"), f"-{num(hit)}")
    z2.metric(L("Marj etkisi", "Margin impact"), f"-{num(hit / REV_MID * 100, 2)} {L('puan', 'pts')}")
    z3.metric(L("Özsermaye etkisi (mn $)", "Equity impact ($m)"), f"-{num(eq_hit, 0)}", delta=pct(-eq_hit / MCAP, 1, sign=True))

    st.markdown("#### " + L("ESG'yi iskonto oranına bağla: risk primi hesaplayıcı", "Link ESG to the discount rate: risk premium calculator"))
    st.caption(L(
        f"Jüriler ESG'yi finansal modelden ayrı görmez; burada ESG, WACC'a eklenen bir prim olarak modele giriyor. Baz WACC ({pp(wacc, 2)}) ve büyüme "
        f"({pp(g_term, 2)}) Değerleme Masası'ndaki reverse DCF ayarlarından geliyor. Prim veri değil, gerekçelendirilmesi gereken bir yargı: düşük halka açıklık, "
        "emisyon verisindeki boşluklar, AB karbon düzenlemesine maruziyet.",
        f"Judges do not see ESG as separate from the financial model; here ESG enters the model as a premium added to WACC. Base WACC ({pp(wacc, 2)}) and growth "
        f"({pp(g_term, 2)}) come from the reverse DCF settings on the Valuation Desk. The premium is not data but a judgement that must be justified: low free "
        "float, gaps in emissions data, exposure to EU carbon rules."))
    prem = st.slider(L("ESG ve yönetişim risk primi (baz puan)", "ESG and governance risk premium (basis points)"), 0, 200, 50, step=10, key="esg_bp")
    fcff_base = v.implied_steady_fcff(EV, wacc / 100, g_term / 100)

    def eq_delta(bp: float) -> float:
        return v.ev_from_fcff(fcff_base, wacc / 100 + bp / 10000, g_term / 100) - EV

    p1, p2 = st.columns([1, 2])
    p1.metric(L("Özsermaye etkisi (mn $)", "Equity impact ($m)"), num(eq_delta(prem), 0), delta=pct(eq_delta(prem) / MCAP, 1, sign=True), help=gl_help("esg_premium"))
    p1.caption(md(L(f"Her 50 baz puan yaklaşık {money(-eq_delta(50), 0)} değer siliyor.", f"Every 50 basis points removes about {money(-eq_delta(50), 0)} of value.")))
    pdf_ = pd.DataFrame([{"bp": b, "d": eq_delta(b)} for b in range(0, 210, 10)])
    p2.altair_chart(alt.Chart(pdf_).mark_area(line={"color": PINK}, color=alt.Gradient(
        gradient="linear", stops=[alt.GradientStop(color="#FBE3F0", offset=0), alt.GradientStop(color=ROSE, offset=1)], x1=1, x2=1, y1=1, y2=0,
    )).encode(x=alt.X("bp:Q", title=L("Risk primi (baz puan)", "Risk premium (basis points)")),
              y=alt.Y("d:Q", title=L("Özsermaye etkisi (mn $)", "Equity impact ($m)"), axis=NUM_AXIS)).properties(height=200), width="stretch")
    st.warning(md(f"**{L('Veri tuzakları (rapora girmemeli):', 'Data traps (must stay out of the report):')}**\n\n" + "\n".join(f"- {t}" for t in E["tuzaklar"])))

# 6. CFA PUAN HARİTASI
with tabs[5]:
    PB = PITCH["cfa_playbook"]
    st.caption(f"{PB['format']} {L('Kaynak', 'Source')}: {src_link('cfa_rules')}")
    ST_KEYS = [L("Başlamadı", "Not started"), L("Taslak", "Draft"), L("Kanıt hazır", "Evidence ready"), L("Rapora hazır", "Report ready")]
    STATUS = dict(zip(ST_KEYS, [0.0, 0.35, 0.7, 1.0]))
    defaults = [ST_KEYS[i] for i in (2, 1, 1, 2, 2, 2, 1)]
    C_B, C_PT, C_D, C_K = L("Bölüm", "Section"), L("Puan", "Points"), L("Durum", "Status"), L("Uygulamadaki kanıt", "Evidence in the app")
    wr = pd.DataFrame([{C_B: r["bolum"], C_PT: r["puan"], C_D: d, C_K: r["kanit"]} for r, d in zip(PB["yazili_rubrik"], defaults)])
    cL, cR = st.columns([3, 2])
    with cL:
        st.markdown("##### " + L("Yazılı rapor rubriği (100 puan)", "Written report rubric (100 points)"))
        wr_ed = st.data_editor(wr, hide_index=True, disabled=[C_B, C_PT, C_K], key=f"rubric_editor_{LG}", width="stretch",
                               column_config={C_D: st.column_config.SelectboxColumn(options=ST_KEYS, required=True)})
        weighted = sum(r[C_PT] * STATUS.get(r[C_D], 0) for _, r in wr_ed.iterrows())
        st.progress(min(weighted / 100, 1.0), text=L(f"Puan ağırlıklı hazırlık: {num(weighted, 0)} / 100", f"Points weighted readiness: {num(weighted, 0)} / 100"))
        st.caption(L("Durumlar takımın kendi değerlendirmesi; ağırlıklar resmi rubrikten. En yüksek puanlı iki bölüm Değerleme ve Finansal Analiz (20+20).",
                     "Statuses are the team's own assessment; weights come from the official rubric. The two highest weighted sections are Valuation and Financial Analysis (20+20)."))
    with cR:
        st.markdown("##### " + L("Sunum rubriği (100 puan)", "Presentation rubric (100 points)"))
        sr = pd.DataFrame(PB["sunum_rubrik"])
        sbars = alt.Chart(sr).mark_bar(color=PINK, cornerRadiusEnd=6, size=20).encode(
            y=alt.Y("bolum:N", sort="-x", title=None, axis=alt.Axis(labelLimit=200)), x=alt.X("puan:Q", title=L("Puan", "Points")))
        st.altair_chart((sbars + sbars.mark_text(align="left", dx=5, color=PLUM).encode(text="puan:Q")).properties(height=250), width="stretch")
        st.caption(L("Soru cevap tek başına 20 puan. Jüri Provası sekmesi tam bunun için.", "Q&A alone is worth 20 points. The Jury Rehearsal tab exists for exactly that."))
    st.markdown("##### " + L("Kazanan raporlarda tekrar eden desenler", "Patterns that recur in winning reports"))
    st.caption(f"{L('İncelenen', 'Reviewed')}: {src_link('waterloo')} · {src_link('niu')}")
    have = [p["desen"] for p in PB["kazanan_desenler"] if p["bizde"]]
    todo = [p["desen"] for p in PB["kazanan_desenler"] if not p["bizde"]]
    k1_, k2_ = st.columns(2)
    k1_.markdown(f"**{L('Bu cockpitte hazır', 'Ready in this cockpit')}**\n\n" + "\n".join(f"- ✅ {h}" for h in have))
    k2_.markdown(f"**{L('Rapor sürecinde eklenecek', 'To be added during the report')}**\n\n" + "\n".join(f"- ⏳ {t}" for t in todo))

# 7. JÜRİ PROVASI
with tabs[6]:
    PB = PITCH["cfa_playbook"]
    st.markdown("##### " + L("Jüri rehberindeki resmi örnek sorular", "Official sample questions from the judge guidelines"))
    st.caption(f"{L('Kaynak', 'Source')}: {src_link('cfa_judge')}. " + L("Jüri sunumu, alım tarafının satış tarafını dinlediği gözle değerlendirir.",
                                                                          "Judges assess the pitch as the buy side listening to a sell side pitch."))
    for q in PB["resmi_juri_sorulari"]:
        st.markdown(f"- *{q}*")

    st.markdown("##### " + L("Prova: önce kendin cevapla, sonra iskeleti aç", "Rehearsal: answer first, then open the outline"))
    for i, q in enumerate(PITCH["jury_questions"]):
        with st.expander(f"❓ {q['soru']}"):
            st.text_area(L("Senin cevabın", "Your answer"), key=f"jury_ans_{i}", height=90,
                         placeholder=L("30 saniyelik cevabını buraya yaz...", "Write your 30 second answer here..."))
            if st.toggle(L("Cevap iskeletini göster", "Show the answer outline"), key=f"jury_show_{i}"):
                st.markdown(md("\n".join(f"- {b}" for b in q["iskelet"])))
                st.error(md(f"**{L('Tuzak', 'Trap')}:** {q['tuzak']}"))

    st.markdown("##### 🧠 " + L("Rakam provası: jüri önünde ezbere bilmen gereken rakamlar", "Number drill: the figures you must know cold in front of the judges"))
    st.caption(L("Şıklar bilerek birbirine karışabilecek gerçek rakamlardan seçildi: eski rehberlik, başka bir dönemin marjı, peer'ın çarpanı gibi.",
                 "The options are deliberately real figures that are easy to confuse: old guidance, another period's margin, a peer's multiple."))
    old_ttm = v.ttm(P["2025"]["favok"], P["1Ç25"]["favok"], P["1Ç26"]["favok"])
    old_mult = (MCAP + P["1Ç26"]["net_borc"]) / old_ttm
    about = L("yaklaşık ", "about ")
    prev_rev = G["onceki"]["gelir_mn_usd"]

    def margin_of(k: str) -> str:
        return pct(P[k]["favok"] / P[k]["gelir"])

    QUIZ = [
        (L("BRSAN'ın son 12 ay FD/FAVÖK çarpanı kaç?", "What is BRSAN's trailing EV/EBITDA?"), f"{num(EV / TTM_EBITDA)}x",
         [f"{num(EV / E26_MID)}x", f"{num(old_mult)}x", f"{num(PEER_TTM[1])}x"],
         L(f"{num(EV / E26_MID)}x ileriye dönük değer, {num(old_mult)}x 1Ç26 verisiyle hesaplanan eski değer, {num(PEER_TTM[1])}x Vallourec.",
           f"{num(EV / E26_MID)}x is the forward figure, {num(old_mult)}x the older value on 1Q26 data, {num(PEER_TTM[1])}x is Vallourec.")),
        (L("Güncel 2026 gelir rehberliği ne?", "What is the current 2026 revenue guidance?"), bn_range(REV_LO, REV_HI),
         [bn_range(*prev_rev), bn_range(1800, 2000), bn_range(2400, 2600)],
         L(f"Rehberlik 2Ç26'da yükseltildi; eski aralık {bn_range(*prev_rev)} idi.", f"Guidance was raised in 2Q26; the old range was {bn_range(*prev_rev)}.")),
        (L("2Ç26 sonunda net borç / FAVÖK kaç (sunum)?", "Net debt / EBITDA at the end of 2Q26 (deck)?"), f"{num(LEV['2Ç26'])}x",
         [f"{num(LEV['2Ç25'])}x", f"{num(LEV['2025'])}x", f"{num(LEV['1Ç26'])}x"],
         L(f"Seri 2Ç25'ten itibaren {num(LEV['2Ç25'])}x, {num(LEV['2025'])}x, {num(LEV['1Ç26'])}x ve {num(LEV['2Ç26'])}x.",
           f"The series from 2Q25 runs {num(LEV['2Ç25'])}x, {num(LEV['2025'])}x, {num(LEV['1Ç26'])}x and {num(LEV['2Ç26'])}x.")),
        (L("1Y26'da gelirin ne kadarı ABD'den geldi?", "What share of 1H26 revenue came from the US?"), pp(US_SHARE, 0),
         [pp(SEG["abd_gelir_payi"]["2024"], 0), pp(SEG["global_gelir_payi_1y26"], 0), pp(s_infra["pay"], 0)],
         L(f"{pp(SEG['abd_gelir_payi']['2024'], 0)} 2024'teki ABD payı, {pp(SEG['global_gelir_payi_1y26'], 0)} toplam yurt dışı payı, "
           f"{pp(s_infra['pay'], 0)} Altyapı ve Proje segmentinin payı.",
           f"{pp(SEG['abd_gelir_payi']['2024'], 0)} was the US share in 2024, {pp(SEG['global_gelir_payi_1y26'], 0)} is the total international share, "
           f"{pp(s_infra['pay'], 0)} is the Infrastructure & Project segment share.")),
        (L("EquityRT'deki mutabık F/K kaç?", "What is the reconciled P/E on EquityRT?"), num(MKT["p_e"], 2),
         [num(MKT["p_e_snapshot_ekrani"], 2), num(SECTOR["p_e"], 2), num(PEER_PE[0], 2)],
         L(f"{num(MKT['p_e_snapshot_ekrani'], 2)} Snapshot ekranındaki farklı bazlı değer, {num(SECTOR['p_e'], 2)} sektör medyanı, {num(PEER_PE[0], 2)} Tenaris.",
           f"{num(MKT['p_e_snapshot_ekrani'], 2)} is the differently based Snapshot figure, {num(SECTOR['p_e'], 2)} the sector median, {num(PEER_PE[0], 2)} Tenaris.")),
        (L("2Ç26 FAVÖK marjı kaç?", "What was the 2Q26 EBITDA margin?"), margin_of("2Ç26"), [margin_of("1Ç26"), margin_of("1Y26"), margin_of("2025")],
         L("Diğerleri 1Ç26, 1Y26 ve 2025 yılı marjları; marjın oynaklığı tezin merkezinde.",
           "The others are the 1Q26, 1H26 and FY2025 margins; margin volatility is at the heart of the thesis.")),
        (L("Altyapı ve Proje sipariş portföyü ne kadar?", "How large is the Infrastructure & Project backlog?"), about + bn_one(BACKLOG),
         [about + bn_one(1900), about + money(NEW_ORDERS, 0), about + bn_one(1800)],
         L(f"{bn_one(1900)} 1Ç26 sunumundaki rakam, {money(NEW_ORDERS, 0)} Ağustos siparişleri, {bn_one(1800)} 2025'te imzalanan kısım.",
           f"{bn_one(1900)} was the 1Q26 deck figure, {money(NEW_ORDERS, 0)} the August orders, {bn_one(1800)} the part signed in 2025.")),
        (L("Payların ne kadarı tek ortakta?", "What share of the stock sits with a single holder?"), pp(77.9),
         [pp(83.93, 2), pp(16.07, 2), pp(PEERS["ownership"]["breakdown"]["institutions_pct"], 2)],
         L(f"{pp(83.93, 2)} grubun toplam payı, {pp(16.07, 2)} halka açık kısım, {pp(PEERS['ownership']['breakdown']['institutions_pct'], 2)} kurumsal yatırımcılar.",
           f"{pp(83.93, 2)} is the group's total stake, {pp(16.07, 2)} the free float, {pp(PEERS['ownership']['breakdown']['institutions_pct'], 2)} institutional investors.")),
        (L("1Y26 serbest nakit akımı ne kadar?", "How much free cash flow in 1H26?"), money(CF["serbest_nakit_akimi"], 0),
         [money(CF["faaliyet_nakdi"], 0), money(CF["isletme_sermayesi"], 0), money(CF["favok"], 0)],
         L(f"{money(CF['faaliyet_nakdi'], 0)} faaliyet nakdi, {money(CF['isletme_sermayesi'], 0)} işletme sermayesi katkısı, {money(CF['favok'], 0)} FAVÖK.",
           f"{money(CF['faaliyet_nakdi'], 0)} is operating cash flow, {money(CF['isletme_sermayesi'], 0)} the working capital contribution, {money(CF['favok'], 0)} EBITDA.")),
    ]
    with st.form(f"quiz_form_{LG}"):
        picks = []
        for i, (q, correct, wrong, _) in enumerate(QUIZ):
            opts = [correct] + wrong
            random.Random(i + 7).shuffle(opts)
            picks.append(st.radio(f"{i + 1}. {q}", opts, index=None, key=f"quiz_{LG}_{i}"))
        checked = st.form_submit_button(L("Cevapları kontrol et", "Check answers"))
    if checked:
        score = sum(1 for p, item in zip(picks, QUIZ) if p == item[1])
        st.metric(L("Skorun", "Your score"), f"{score} / {len(QUIZ)}")
        for i, (p, (q, correct, _, why)) in enumerate(zip(picks, QUIZ)):
            if p == correct:
                st.success(md(f"{i + 1}. ✅ {correct}. {why}"))
            else:
                st.error(md(f"{i + 1}. ❌ {L('Doğrusu', 'Correct answer')}: {correct}. {why}"))
        if ME:
            get_board().record_score(ME, score, len(QUIZ))
            st.caption(L("Skorun Takım Masası'ndaki tabloya yazıldı.", "Your score was posted to the Team Desk leaderboard."))
        else:
            st.caption(L("Skorunu takım tablosuna yazmak için Takım Masası sekmesinde adını gir.", "Enter your name on the Team Desk tab to post your score to the team leaderboard."))

    st.markdown("##### " + L("60 saniyelik İngilizce pitch", "60 second pitch"))
    pitch = (
        f"Borusan Boru is a Turkish steel pipe maker with ten plants on three continents and 1.7 million tons of capacity; {US_SHARE}% of its first half "
        f"2026 revenue came from the United States. Three facts frame our work. First, visibility: management raised 2026 guidance to {REV_LO / 1000:.1f} to "
        f"{REV_HI / 1000:.1f} billion dollars of revenue at a {M_LO * 100:.0f} to {M_HI * 100:.0f}% EBITDA margin, backed by an infrastructure order book of "
        f"about {BACKLOG / 1000:.1f} billion dollars and roughly {NEW_ORDERS:,.0f} million dollars of new US orders announced in August. Second, a repaired "
        f"balance sheet: net debt to EBITDA fell from {LEV['2Ç25']:.1f}x to {LEV['2Ç26']:.1f}x in a year. Third, the debate: on trailing numbers the stock trades "
        f"at about {EV / TTM_EBITDA:.1f}x EV/EBITDA, well above Tenaris and Vallourec, but on the midpoint of the new guidance it is close to {EV / E26_MID:.1f}x, "
        "near Tenaris. So the question our report answers is simple: is the 11.5% second quarter margin the new normal, or a one off project mix? "
        "If it holds, the premium is earned. If it fades, that is the key risk."
    )
    st.markdown(f"> {pitch}")
    st.caption(L("Rakamlar sayfadaki hesaplardan otomatik geliyor; veri güncellenince pitch de güncellenir.",
                 "Figures come straight from the page's calculations; when the data is updated, the pitch updates too."))

    st.markdown("##### " + L("10 dakikalık sunum akışı (sunum rubriğine göre)", "10 minute presentation flow (mapped to the presentation rubric)"))
    C_T, C_SEC, C_RUB = L("Süre", "Time"), L("Bölüm", "Section"), L("Rubrikteki karşılığı", "Rubric line")
    flow = pd.DataFrame([
        {C_T: L("1,5 dk", "1.5 min"), C_SEC: L("Tavsiye ve tez", "Recommendation and thesis"), C_RUB: "Presentation (20)"},
        {C_T: L("1,5 dk", "1.5 min"), C_SEC: L("Şirket, sektör, peer seçimi", "Company, industry, peer selection"), C_RUB: "Presentation / Financial Analysis"},
        {C_T: L("2,5 dk", "2.5 min"), C_SEC: L("Finansal analiz: marj, kaldıraç, nakit kalitesi", "Financial analysis: margin, leverage, cash quality"), C_RUB: "Financial Analysis (20)"},
        {C_T: L("2,5 dk", "2.5 min"), C_SEC: L("Değerleme: football field, senaryo, reverse DCF", "Valuation: football field, scenarios, reverse DCF"), C_RUB: "Valuation (20)"},
        {C_T: L("1 dk", "1 min"), C_SEC: L("Riskler ve azaltıcılar", "Risks and mitigants"), C_RUB: "Presentation"},
        {C_T: L("1 dk", "1 min"), C_SEC: L("ESG ve değerlemeye etkisi", "ESG and its valuation impact"), C_RUB: "ESG (10)"},
    ])
    st.dataframe(flow, hide_index=True)


# 8. TAKIM MASASI
@st.fragment(run_every=10)
def consensus_panel() -> None:
    votes = get_board().snapshot()["votes"]
    st.markdown("##### 📡 " + L("Canlı konsensüs", "Live consensus"))
    if not votes:
        st.info(L("Henüz oy yok. İlk oyu sen ver; bu panel her 10 saniyede kendini yeniler.", "No votes yet. Cast the first one; this panel refreshes itself every 10 seconds."))
        return
    df = pd.DataFrame([{"name": n, "call": REC.get(d["call"], d["call"]), "code": d["call"], "target": d["target"],
                        "up": v.upside(d["target"], MCAP), "thesis": d["thesis"], "risk": d["risk"], "ts": d["ts"]} for n, d in votes.items()])
    med = float(df["target"].median())
    c1, c2, c3 = st.columns(3)
    c1.metric(L("Oy sayısı", "Votes"), len(df))
    c2.metric(L("Medyan hedef (mn $)", "Median target ($m)"), num(med, 0), delta=pct(v.upside(med, MCAP), 1, sign=True))
    c3.metric(L("Dağılım", "Split"), " · ".join(f"{REC[k]} {int((df['code'] == k).sum())}" for k in REC))
    pts = alt.Chart(df).mark_circle(size=260, opacity=0.9, stroke="white", strokeWidth=2).encode(
        x=alt.X("target:Q", title=L("Hedef piyasa değeri (mn $)", "Target market value ($m)"), scale=alt.Scale(zero=False), axis=NUM_AXIS),
        y=alt.Y("name:N", title=None),
        color=alt.Color("call:N", scale=alt.Scale(domain=[REC["BUY"], REC["HOLD"], REC["SELL"]], range=[GREEN, LAV, RED]), legend=alt.Legend(orient="bottom", title=None)),
        tooltip=["name:N", "call:N", "target:Q", "thesis:N"])
    now_rule = alt.Chart(pd.DataFrame({"x": [MCAP]})).mark_rule(color=PLUM, strokeDash=[6, 4], size=2).encode(x="x:Q")
    st.altair_chart((pts + now_rule).properties(height=max(140, 46 * len(df))), width="stretch")
    table = pd.DataFrame({
        L("İsim", "Name"): df["name"], L("Tavsiye", "Call"): df["call"], L("Hedef", "Target"): df["target"].map(lambda t: num(t, 0)),
        L("Potansiyel", "Upside"): df["up"].map(lambda u: pct(u, 1, sign=True)), L("Tez", "Thesis"): df["thesis"], "Risk": df["risk"], L("Zaman", "Time"): df["ts"]})
    st.dataframe(table, hide_index=True)
    if len(df) > 1:
        spread = float(df["target"].max() - df["target"].min())
        st.caption(md(L(f"Hedefler arasındaki fark {money(spread, 0)}. Fark büyükse komitede önce varsayımlar tartışılmalı, sonra tavsiye.",
                        f"The gap between targets is {money(spread, 0)}. If it is wide, the committee should debate assumptions first, then the call.")))
    st.caption(L("Her 10 saniyede otomatik yenilenir.", "Refreshes automatically every 10 seconds."))


with tabs[7]:
    board = get_board()
    st.caption(L(
        "Bu masa, uygulamayı aynı anda açık tutan herkes için ortaktır ve canlı güncellenir. Uygulama yeniden başlarsa sıfırlanır; bu yüzden aşağıdan JSON "
        "yedeği alınabilir. Kalıcı kayıt için sıradaki adım Supabase bağlantısı.",
        "This desk is shared by everyone who has the app open at the same time and updates live. It resets if the app restarts, so a JSON backup can be "
        "downloaded below. The next step for permanent storage is a Supabase connection."))
    st.text_input(L("Adın (takımda böyle görünecek)", "Your name (this is how the team sees you)"), key="me_name", placeholder="Selin")
    v1, v2 = st.columns([2, 3])
    with v1:
        st.markdown("##### 🗳️ " + L("Yatırım komitesi oyu", "Investment committee vote"))
        with st.form(f"vote_form_{LG}"):
            call = st.radio(L("Tavsiyen", "Your call"), list(REC.keys()), format_func=lambda k: REC[k], horizontal=True, index=1)
            target = st.number_input(L("Hedef piyasa değeri (mn $)", "Target market value ($m)"), min_value=200.0, max_value=6000.0,
                                     value=float(round(MCAP)), step=25.0)
            thesis_txt = st.text_input(L("Tez cümlen", "Your thesis in one sentence"))
            risk_txt = st.text_input(L("En büyük risk", "Biggest risk"))
            sent = st.form_submit_button(L("Oyumu kaydet", "Submit my vote"))
        if sent:
            if ME:
                board.vote(ME, call, target, thesis_txt, risk_txt)
                st.success(L("Oyun kaydedildi.", "Your vote is in."))
            else:
                st.warning(L("Önce Takım Masası sekmesinde adını yaz.", "Enter your name on the Team Desk tab first."))
        st.caption(md(L(f"Bugünkü piyasa değeri {money(MCAP)}; hedefin bunun üstündeyse yukarı potansiyel görüyorsun.",
                        f"Market value today is {money(MCAP)}; a target above it means you see upside.")))
    with v2:
        consensus_panel()

    st.markdown("##### 🧩 " + L("Görev dağılımı: rubrik bölümleri kimde?", "Ownership: who owns which rubric section?"))
    sections = [r["bolum"] for r in PITCH["cfa_playbook"]["yazili_rubrik"]]
    points_of = {r["bolum"]: r["puan"] for r in PITCH["cfa_playbook"]["yazili_rubrik"]}
    o1, o2 = st.columns([2, 3])
    with o1:
        with st.form(f"own_form_{LG}"):
            mine = st.multiselect(L("Sorumlu olduğun bölümler", "Sections you own"), sections)
            role = st.text_input(L("Rolün", "Your role"), placeholder=L("Örn. değerleme lideri", "e.g. valuation lead"))
            own_ok = st.form_submit_button(L("Kaydet", "Save"))
        if own_ok:
            if ME:
                board.set_member(ME, role, mine)
                st.success(L("Görev dağılımı güncellendi.", "Ownership updated."))
            else:
                st.warning(L("Önce Takım Masası sekmesinde adını yaz.", "Enter your name on the Team Desk tab first."))
    with o2:
        members = board.snapshot()["members"]
        cov = []
        for s in sections:
            owners = [nm for nm, m in members.items() if s in m["sections"]]
            cov.append({L("Bölüm", "Section"): s, L("Puan", "Points"): points_of[s],
                        L("Sorumlu", "Owner"): ", ".join(owners) if owners else L("⚠️ sahipsiz", "⚠️ unassigned")})
        st.dataframe(pd.DataFrame(cov), hide_index=True)
        if members:
            st.caption(" · ".join(
                f"{nm} ({m['role'] or L('rol yok', 'no role')}): {sum(points_of.get(s, 0) for s in m['sections'])} {L('puan', 'pts')}" for nm, m in members.items()))

    sb1, sb2 = st.columns(2)
    snap = board.snapshot()
    with sb1:
        st.markdown("##### 📚 " + L("Senaryo kütüphanesi", "Scenario library"))
        if not snap["scenarios"]:
            st.caption(L("Değerleme Masası'ndan kaydedilen senaryolar burada link olarak görünür.", "Scenarios saved from the Valuation Desk appear here as links."))
        for sc in snap["scenarios"]:
            st.markdown(md(f"- **[{sc['name']}]({sc['url']})** · {sc['author']} · {sc['summary']} · {sc['ts']}"))
    with sb2:
        st.markdown("##### 🏅 " + L("Rakam provası skor tablosu", "Number drill leaderboard"))
        if not snap["scores"]:
            st.caption(L("Jüri Provası'ndaki rakam testini çözen herkes burada görünür.", "Everyone who takes the number drill in Jury Rehearsal appears here."))
        else:
            C_N, C_LAST, C_BEST, C_TIME = L("İsim", "Name"), L("Son", "Last"), L("En iyi", "Best"), L("Zaman", "Time")
            sdf2 = pd.DataFrame([{C_N: nm, C_LAST: f"{d['last']}/{d['total']}", C_BEST: d["best"], C_TIME: d["ts"]} for nm, d in snap["scores"].items()])
            st.dataframe(sdf2.sort_values(C_BEST, ascending=False), hide_index=True)

    st.markdown("##### 💾 " + L("Yedek", "Backup"))
    bk1, bk2 = st.columns(2)
    bk1.download_button(L("Panoyu JSON olarak indir", "Download the board as JSON"), board.export_json(), file_name="takim_masasi.json", mime="application/json")
    up = bk2.file_uploader(L("Yedekten geri yükle", "Restore from backup"), type=["json"], key="board_upload")
    if up is not None and bk2.button(L("Geri yükle", "Restore")):
        try:
            board.load(json.load(up))
            st.success(L("Pano geri yüklendi.", "Board restored."))
        except Exception:
            st.error(L("Dosya okunamadı.", "The file could not be read."))

st.markdown("---")
st.caption(L(
    "SS Academic Coach · Borusan Equity Cockpit. Hesap çekirdeği utils/valuation.py içinde ve birim testli; veriler data/brsan_pitch.json ile "
    "data/cfa_peers.json dosyalarında, her biri kaynağıyla. Hiçbir rakam tahminle doldurulmadı.",
    "SS Academic Coach · Borusan Equity Cockpit. The calculation core lives in utils/valuation.py with unit tests; the data sits in data/brsan_pitch.json "
    "and data/cfa_peers.json, each figure with its source. No number was filled in with a guess."))
