import datetime
import json
import random
from pathlib import Path

import streamlit as st

from utils.theme import inject_theme

st.set_page_config(page_title="Değerleme Akademisi", page_icon="🎯", layout="wide")
inject_theme()

BASE = Path(__file__).parent.parent / "data" / "how_to_value"
content = json.loads((BASE / "content.json").read_text(encoding="utf-8"))
pitch = json.loads((Path(__file__).parent.parent / "data" / "brsan_pitch.json").read_text(encoding="utf-8"))
SLIDES, QUESTIONS, NUM = content["slides"], content["questions"], content["numbers"]

LEVELS = {1: ("Mutlaka bil", ""), 2: ("Anla", "green"), 3: ("Detay", "amber")}
RATINGS = ["Henüz bakmadım", "Bilemedim", "Emin değilim", "Bildim"]
WEIGHT = {"Henüz bakmadım": 3, "Bilemedim": 5, "Emin değilim": 3, "Bildim": 1}


def rating_radio(label: str, n: int, key: str, horizontal: bool = True) -> str:
    """Radio whose default comes from saved progress; no index once the widget owns its state."""
    current = ss["htv_q"].get(str(n), "Henüz bakmadım")
    if key in ss:
        return st.radio(label, RATINGS, horizontal=horizontal, key=key)
    return st.radio(label, RATINGS, horizontal=horizontal, index=RATINGS.index(current), key=key)


def pill(level: int) -> str:
    text, cls = LEVELS[level]
    return f'<span class="sac-pill {cls}">{text}</span>'


# ---- progress lives in session state; it can be saved as a file and loaded back the next day
ss = st.session_state
ss.setdefault("htv_slides", {})
ss.setdefault("htv_q", {})
ss.setdefault("htv_tasks", {})

PLAN = [
    ("Pazar 4 Ekim", [
        "Gerçek hayat sekmesini oku, bugüne indirme hesaplayıcısıyla oyna",
        "Slayt 1 ile 4: Önce öğren ve Türkçe metin",
        "Nasıl yapılır: 0. bölüm (bugüne indirmek) ve öz test 1, 2",
    ]),
    ("Pazartesi 5 Ekim", [
        "Slayt 5 ile 8: Önce öğren, Türkçe metin, English script",
        "Nasıl yapılır: 3. bölüm, WACC'ı Excel'de kendin kur",
        "Jüri provası: Mutlaka bil sorularının hepsi",
    ]),
    ("Salı 6 Ekim", [
        "Slayt 9 ile 12: üç sekmenin hepsi",
        "Nasıl yapılır: 6 ile 10. bölüm, DCF ve reverse DCF'i Excel'de kur",
        "Tam İngilizce prova, süre tut (hedef 6 dakika)",
    ]),
    ("Çarşamba 7 Ekim (sunum günü)", [
        "Sabah: Bilemedim ve Emin değilim işaretli soruları tekrar et",
        "Bir tam prova, sonra bırak ve dinlen",
    ]),
]
ALL_TASKS = [f"{d}::{t}" for d, ts in PLAN for t in ts]

# ---- header
st.title("🎯 Değerleme Akademisi")
st.caption("How to Value a Company · CFA Institute'un değerleme süreci, gelişmekte olan piyasalara uyarlanmış, Borusan Boru üzerinde uygulanmış")

DEADLINE = datetime.date.fromisoformat(content["meta"]["presentation_date"])
days_left = (DEADLINE - datetime.date.today()).days
if days_left > 0:
    st.error(f"⏳ Sunuma {days_left} gün kaldı · Çarşamba 7 Ekim 2026")
elif days_left == 0:
    st.success("🎤 Bugün sunum günü. Sakin ol: mantığı biliyorsun, rakamlar slaytta.")

known_s = sum(1 for s in SLIDES if ss["htv_slides"].get(str(s["n"])))
known_q = sum(1 for q in QUESTIONS if ss["htv_q"].get(str(q["n"])) == "Bildim")
done_t = sum(1 for k in ALL_TASKS if ss["htv_tasks"].get(k))
c1, c2, c3 = st.columns(3)
c1.metric("Öğrendiğim slaytlar", f"{known_s} / {len(SLIDES)}")
c2.metric("Bildiğim jüri soruları", f"{known_q} / {len(QUESTIONS)}")
c3.metric("Plan görevleri", f"{done_t} / {len(ALL_TASKS)}")
st.progress((known_s + known_q + done_t) / (len(SLIDES) + len(QUESTIONS) + len(ALL_TASKS)))
st.markdown(
    f'{pill(1)} &nbsp; sunumda ve soru cevapta mutlaka bilmen gereken &nbsp;&nbsp; {pill(2)} &nbsp; mantığını anlaman yeterli &nbsp;&nbsp; {pill(3)} &nbsp; merak edersen',
    unsafe_allow_html=True,
)

tabs = st.tabs(["📅 Plan", "🖥️ Sunum", "🌍 Gerçek hayat", "🧮 Nasıl yapılır", "🎤 Jüri provası", "📖 Sözlük", "🏆 CFA'de"])

# ======== PLAN
with tabs[0]:
    st.subheader("Çarşambaya kadar çalışma planı")
    st.caption("Her gün yaklaşık 1 ile 1,5 saat. Rakamları ezberlemen gerekmiyor; mantığı bilmen yeterli. Jüri ezberi değil, düşünceyi ölçer.")
    cols = st.columns(len(PLAN))
    for col, (day, tasks) in zip(cols, PLAN):
        with col:
            st.markdown(f'<div class="sac-card"><h4>{day}</h4></div>', unsafe_allow_html=True)
            for t in tasks:
                key = f"{day}::{t}"
                ss["htv_tasks"][key] = st.checkbox(t, value=ss["htv_tasks"].get(key, False), key=f"task_{key}")

    st.markdown("#### Dosyalar")
    d1, d2 = st.columns(2)
    d1.download_button("📥 Sunumu indir (PowerPoint)", (BASE / content["meta"]["deck"]).read_bytes(), file_name=content["meta"]["deck"],
                       mime="application/vnd.openxmlformats-officedocument.presentationml.presentation", width="stretch")

    st.markdown("#### İlerlemeni sakla")
    st.caption("Uygulama sayfa yenilenince işaretlerini unutur. Günün sonunda dosyayı indir, ertesi gün yükle; kaldığın yerden devam edersin.")
    state = {"slides": ss["htv_slides"], "q": ss["htv_q"], "tasks": ss["htv_tasks"], "saved": datetime.datetime.now().isoformat(timespec="minutes")}
    d2.download_button("💾 İlerlememi indir", json.dumps(state, ensure_ascii=False), file_name="degerleme_ilerleme.json", mime="application/json", width="stretch")
    up = st.file_uploader("İlerleme dosyanı yükle", type="json", key="htv_upload")
    if up is not None and ss.get("htv_loaded") != up.name + str(up.size):
        data = json.loads(up.read().decode("utf-8"))
        ss["htv_slides"], ss["htv_q"], ss["htv_tasks"] = data.get("slides", {}), data.get("q", {}), data.get("tasks", {})
        ss["htv_loaded"] = up.name + str(up.size)
        for k in list(ss.keys()):
            if k.startswith(("task_", "known_", "rate_")):
                del ss[k]
        st.rerun()

# ======== SLIDES
with tabs[1]:
    st.subheader("Sunum, slayt slayt")
    st.caption(f"12 ana slayt. İngilizce metin toplam yaklaşık 6 dakika. Her slaytta üç tur: önce öğren, sonra Türkçe akışı otur, en son İngilizce söyle.")
    for s in SLIDES:
        mark = "✅ " if ss["htv_slides"].get(str(s["n"])) else ""
        with st.expander(f"{mark}{s['n']}. {s['title']}"):
            st.markdown(pill(s["level"]), unsafe_allow_html=True)
            st.image(str(BASE / s["image"]), width="stretch")
            t1, t2, t3, t4 = st.tabs(["📚 Önce öğren", "🇹🇷 Türkçe metin", "🇬🇧 English script", "🔁 Explained again"])
            t1.markdown(s["learn"])
            t2.markdown(s["tr"])
            t3.markdown(f"> {s['en']}")
            t3.caption(f"{len(s['en'].split())} kelime, yaklaşık {round(len(s['en'].split()) / 2.3)} saniye")
            t4.markdown(s["again"])
            if s["keywords"]:
                t4.markdown(f"**Key words:** {s['keywords']}")
            ss["htv_slides"][str(s["n"])] = st.checkbox("Bu slaytı anlatabiliyorum", value=ss["htv_slides"].get(str(s["n"]), False), key=f"known_{s['n']}")
    st.markdown("#### Ek slaytlar (soru cevap için)")
    a1, a2, a3 = st.columns(3)
    for col, i, cap in zip((a1, a2, a3), (13, 14, 15), ("A1 · WACC girdileri", "A2 · DCF ve reverse DCF matematiği", "A3 · On jüri sorusu")):
        col.image(str(BASE / "slides" / f"s-{i:02d}.jpg"), caption=cap, width="stretch")

# ======== REAL LIFE
with tabs[2]:
    st.subheader("Gerçek hayatta değerleme: geleceği bulup bugüne indirmek")
    st.markdown(f'{pill(1)}', unsafe_allow_html=True)
    st.markdown(
        "**Tek cümle:** Gelecekte alacağın para, bugünkü paradan daha az değerlidir. *Bugüne indirmek* = **bölmek**. "
        "%10 istiyorsan 1 yıl sonraki 110 dolar bugün 110 / 1,10 = 100 dolar eder; 2 yıl uzaktaysa iki kez bölersin."
    )
    with st.container(border=True):
        st.markdown("**Kendin dene: bugünkü değer hesaplayıcısı**")
        p1, p2, p3 = st.columns(3)
        amount = p1.number_input("Gelecekteki tutar ($)", value=100.0, step=10.0, key="pv_amt")
        years = p2.number_input("Kaç yıl sonra", value=10, min_value=0, max_value=50, step=1, key="pv_yrs")
        rate = p3.selectbox("Oran", [f"ABD fabrikası %{NUM['wacc_us']:.1f}", f"Türkiye fabrikası %{NUM['wacc_tr']:.1f}", "Örnek %10"], key="pv_rate")
        r = {0: NUM["wacc_us"], 1: NUM["wacc_tr"], 2: 10.0}[[f"ABD fabrikası %{NUM['wacc_us']:.1f}", f"Türkiye fabrikası %{NUM['wacc_tr']:.1f}", "Örnek %10"].index(rate)] / 100
        pv = amount / (1 + r) ** years
        st.markdown(f'<div class="sac-big">{pv:,.1f} $</div>'.replace(",", "X").replace(".", ",").replace("X", "."), unsafe_allow_html=True)
        st.caption(f"{amount:,.0f} / (1 + {r:.3f})^{years}  ·  Excel: =A1/(1+B1)^C1")

    st.markdown("#### Bir analist bu işi gerçekte nasıl yapar?")
    steps = [
        (2, "Geçmişi Excel'e dök", "Son 5 yılın gelir tablosu, bilanço ve nakit akış tablosu: Kamuyu Aydınlatma Platformu (KAP) ya da EquityRT. Her kalemi gelirin yüzdesi olarak hesapla. Bunlar senin \"normalin\"."),
        (1, "Sürücüleri bul", "Kârı doğrudan tahmin etmezsin. Borusan için **hacim (ton) × ton başına fiyat = gelir**. Hacim: sipariş portföyü ve KAP sipariş bildirimleri. Fiyat: çelik rulo fiyatları, ABD gümrük duvarı. Marj: geçmiş (%6,0 → %7,4) ve rehberlik (%9 ile %11)."),
        (2, "Bilgiyi gerçek kaynaklardan topla", "Yatırımcı sunumu ve faaliyet raporu; telekonferans (earnings call), yönetimin analist sorularına cevabı; yatırımcı ilişkileri görüşmesi; sektör verisi; konsensüs (diğer analistlerin tahmin ortalaması, EquityRT ve Bloomberg). Konsensüsten farklıysan nedenini bil."),
        (1, "5 yıllık tahmin tablosunu kur", "Her yıl: gelir → Faiz, Amortisman ve Vergi Öncesi Kâr (FAVÖK) → eksi vergi → eksi yatırım harcaması → eksi işletme sermayesi artışı = **Firmaya Serbest Nakit Akışı (FCFF)**."),
        (1, "Bugüne indir ve uç değeri ekle", "Her yılın nakdini, kaç yıl uzaktaysa o kadar kez (1 + Ağırlıklı Ortalama Sermaye Maliyeti) ile böl. 5. yıldan sonrası: sonraki yılın nakdi / (oran eksi büyüme). Hepsini topla: **Firma Değeri**."),
        (3, "Sağlama yap", "Çarpanla kontrol et, konsensüsle karşılaştır, senaryo kur, her çeyrek güncelle. Excel düzeni: girdiler mavi, formüller siyah, varsayımlar tek sayfada."),
    ]
    for i, (lvl, t, d) in enumerate(steps, 1):
        st.markdown(f'<div class="sac-card"><span class="sac-pill {LEVELS[lvl][1]}">{LEVELS[lvl][0]}</span><h4>{i}. {t}</h4></div>', unsafe_allow_html=True)
        st.markdown(d)

    st.markdown("#### 5 yıllık örnek: nakdi bugüne indir")
    st.caption("Nakit rakamları öğretmek için seçilmiş örnek rakamlar; Borusan'ın gerçek tahmini değil. Kaydırıcıları oynat.")
    s1, s2 = st.columns(2)
    w = s1.slider("Oran (WACC), %", 7.0, 15.0, float(NUM["wacc_blend"]), 0.25, key="dcf_w") / 100
    g = s2.slider("Uzun vadeli büyüme (g), %", 0.0, 4.5, 2.5, 0.25, key="dcf_g") / 100
    cash = [115, 120, 125, 128, 131]
    rows, total = [], 0.0
    for i, c in enumerate(cash, 1):
        div = (1 + w) ** i
        total += c / div
        rows.append({"Yıl": str(2025 + i), "Nakit (örnek)": c, "Bölen": round(div, 3), "Bugünkü değer": round(c / div, 1)})
    tv = cash[-1] * (1 + g) / (w - g)
    ptv = tv / (1 + w) ** 5
    rows.append({"Yıl": "Uç değer (2030 sonrası)", "Nakit (örnek)": round(tv), "Bölen": round((1 + w) ** 5, 3), "Bugünkü değer": round(ptv, 1)})
    st.dataframe(rows, width="stretch", hide_index=True)
    m1, m2, m3 = st.columns(3)
    m1.metric("İlk 5 yılın değeri", f"{total:,.0f}")
    m2.metric("Uç değerin bugünkü değeri", f"{ptv:,.0f}")
    m3.metric("Firma Değeri", f"{total + ptv:,.0f}", f"değerin %{ptv / (total + ptv) * 100:.0f}'i 5. yıldan sonra", delta_color="off")

    st.markdown("#### Hoca \"neden 5 yıllık tahmin yok?\" derse")
    st.info("**\"This is a simplified single stage model. My next step is a five year forecast built on the order book delivery schedule.\"**\n\n"
            "Bu basitleştirilmiş, tek aşamalı bir model. Sıradaki adımım, sipariş portföyünün teslim takvimine dayanan 5 yıllık bir tahmin kurmak.")

# ======== HOW-TO
with tabs[3]:
    st.subheader("Nasıl yapılır: bütün değerlemeyi kendi elinle kur")
    st.caption("Türkçe Excel: ondalık virgül (9,4), formül ayırıcısı noktalı virgül (;). Sırayla git; her adım bir öncekinin üstüne kuruluyor.")
    for sec in content["howto"]:
        with st.expander(sec["title"], expanded=sec["title"].startswith("0.")):
            st.markdown(sec["body"])

# ======== JURY PRACTICE
with tabs[4]:
    st.subheader("Jüri provası")
    st.caption("Rastgele soru, zorlandığın soruları daha sık getirir: 'Bilemedim' işaretlediklerin önce gelir. Önce kendi cevabını yaz ya da sesli söyle, sonra cevabı aç.")
    if st.button("🎲 Bana bir soru sor", key="draw"):
        pool = [q for q in QUESTIONS for _ in range(WEIGHT[ss["htv_q"].get(str(q["n"]), "Henüz bakmadım")])]
        ss["htv_current"] = random.choice(pool)["n"]
    cur = next((q for q in QUESTIONS if q["n"] == ss.get("htv_current")), None)
    if cur:
        with st.container(border=True):
            st.markdown(f'{pill(cur["level"])} &nbsp; **Faruk Hoca:** *"{cur["q"]}"*', unsafe_allow_html=True)
            st.text_area("Senin cevabın (İngilizce dene)", key=f"ans_{cur['n']}", height=90)
            if st.toggle("Örnek cevabı göster", key=f"show_{cur['n']}"):
                st.markdown(f"**Mantık:** {cur['tr']}")
                st.markdown(f"**Söyleyeceğin:** \"{cur['en']}\"")
            st.markdown("**Nasıl gitti?**")
            b1, b2, b3 = st.columns(3)
            for col, label in zip((b1, b2, b3), ("Bildim", "Emin değilim", "Bilemedim")):
                if col.button(label, key=f"cur_{label}_{cur['n']}", width="stretch"):
                    ss["htv_q"][str(cur["n"])] = label
                    ss[f"rate_{cur['n']}"] = label
            st.caption(f"Şu anki durum: {ss['htv_q'].get(str(cur['n']), 'Henüz bakmadım')}")
    st.markdown("#### Bütün sorular")
    for q in QUESTIONS:
        status = ss["htv_q"].get(str(q["n"]), "Henüz bakmadım")
        icon = {"Bildim": "✅", "Emin değilim": "🟡", "Bilemedim": "🔴"}.get(status, "⚪")
        with st.expander(f"{icon} {q['n']}. {q['q']}"):
            st.markdown(pill(q["level"]) + (f' &nbsp; <span class="sac-src">{q["note"]}</span>' if q["note"] else ""), unsafe_allow_html=True)
            st.markdown(f"**Mantık:** {q['tr']}")
            st.markdown(f"**Söyleyeceğin:** \"{q['en']}\"")
            ss["htv_q"][str(q["n"])] = rating_radio("Durum", q["n"], f"rate_{q['n']}")

# ======== GLOSSARY
with tabs[5]:
    st.subheader("Kısaltmalar sözlüğü")
    term = st.text_input("Ara (ör. WACC, FAVÖK, uç değer)", key="gloss_q").strip().lower()
    rows = [r for r in content["glossary"] if not term or term in " ".join(r.values()).lower()]
    for r in rows:
        st.markdown(f'<div class="sac-card"><span class="sac-pill">{r["kisaltma"]}</span><h4>{r["turkce"]}</h4>'
                    f'<p><em>{r["ingilizce"]}</em></p><p>{r["tek_cumle"]}</p></div>', unsafe_allow_html=True)

# ======== CFA
with tabs[6]:
    pb = pitch["cfa_playbook"]
    st.subheader("Bu sunumu gerçek CFA Research Challenge'a taşımak")
    st.markdown(f"**Format:** {pb['format']}")
    st.markdown("**CFA'nın değerleme süreci (müfredat):** işi anla → performansı tahmin et → modeli seç → tahmini değere çevir → sonuca ve tavsiyeye dönüştür. "
                "Bizim sunumumuz bu beş adımın üstüne kurulu; gelişmekte olan piyasa için ülke riski ve ortaklık yapısı adımlarını ekledik.")
    r1, r2 = st.columns(2)
    with r1:
        st.markdown("**Sunum puanlaması**")
        st.dataframe([{"Bölüm": x["bolum"], "Puan": x["puan"]} for x in pb["sunum_rubrik"]], hide_index=True, width="stretch")
    with r2:
        st.markdown("**Yazılı rapor puanlaması**")
        st.dataframe([{"Bölüm": x["bolum"], "Puan": x["puan"]} for x in pb["yazili_rubrik"]], hide_index=True, width="stretch")
    st.markdown("#### Kazanan takımlarda olup bizde henüz olmayanlar")
    for x in pb["kazanan_desenler"]:
        if not x["bizde"]:
            st.markdown(f"- {x['desen']}")
    st.markdown("#### Yarışma versiyonu için sıradaki adımlar")
    st.markdown(
        "- 5 yıllık, sipariş teslim takvimine dayanan üç aşamalı DCF\n"
        "- KAP coğrafi bölüm dipnotuyla ABD ve Türkiye ayrımını gerçek veriye çevirmek\n"
        "- Dar emsal grubu: Tenaris, Vallourec ve diğer boru üreticilerinin Firma Değeri / FAVÖK çarpanları\n"
        "- Hedef fiyat ve tavsiye (yarışma bunu ister; bu sunum bilerek yöntem sunumu)\n"
        "- 10 sayfalık yazılı rapor ve 10 dakikalık sunum için içeriği genişletmek"
    )
    st.caption("Kaynak: CFA Institute Research Challenge resmi kuralları ve jüri rehberi; Equity Valuation: Applications and Processes (2026).")
