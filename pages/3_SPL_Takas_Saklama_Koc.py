import datetime
import json
import random
from pathlib import Path

import streamlit as st

from utils.bug_tracker import BugTracker
from utils.supabase_client import get_supabase_client
from utils.theme import inject_theme

st.set_page_config(page_title="SPL Takas ve Saklama Koçu", page_icon="🧭", layout="wide")
inject_theme()

client = get_supabase_client()
bug_tracker = BugTracker(supabase_client=client)

DEADLINE = datetime.date(2026, 10, 2)
today = datetime.date.today()
days_left = (DEADLINE - today).days

MODULES_PATH = Path(__file__).parent.parent / "data" / "official_spk_modules.json"
module_data = json.loads(MODULES_PATH.read_text(encoding="utf-8"))
m01 = next(m for m in module_data["modules"] if m["module_id"] == "M01")

LESSONS_PATH = Path(__file__).parent.parent / "data" / "spl_lessons" / "M01.json"
lessons_data = json.loads(LESSONS_PATH.read_text(encoding="utf-8"))
lessons_by_id = {b["id"]: b for b in lessons_data["bolumler"]}

st.title("🧭 SPL Takas ve Saklama Koçu")
st.caption("Ders Kodu 1012 — kaynak: 1012_MKT_30062026 (SPK/Takasbank/MKK ortak yayını, 189 sayfa)")

if days_left >= 0:
    st.error(f"⏳ Sınava {days_left} gün kaldı — 2 Ekim 2026")
else:
    st.warning("Sınav tarihi geçti.")

TOC_STATIC = [
    {"Bölüm": "1", "Konu": "Takas ve Saklamaya İlişkin Temel Kavramlar", "Sayfa": "1-6"},
    {"Bölüm": "2.1", "Konu": "MKK Kuruluş/Faaliyet/Çalışma/Denetim Yönetmeliği", "Sayfa": "7-14"},
    {"Bölüm": "2.2", "Konu": "Kaydileştirme Tebliği", "Sayfa": "15-27"},
    {"Bölüm": "2.3", "Konu": "Merkezi Takas ile MKT Uygulaması", "Sayfa": "28-58"},
    {"Bölüm": "2.4", "Konu": "Portföy Saklama Hizmeti Tebliği (III-56.1)", "Sayfa": "59-70"},
    {"Bölüm": "3", "Konu": "BİAŞ Pay Piyasası Takas/Temerrüt/Transfer", "Sayfa": "71-87"},
    {"Bölüm": "4", "Konu": "Borçlanma Araçları Transfer/Takas/Temerrüt", "Sayfa": "88-130"},
    {"Bölüm": "5", "Konu": "Türev Araçlarda Takas, Uzlaşma, Fiziki Teslimat", "Sayfa": "131-162"},
    {"Bölüm": "6", "Konu": "Takasbank Teminat Yönetimi", "Sayfa": "163-174"},
]
TOC = [
    {**row, "Durum": "İşlendi" if row["Bölüm"] in lessons_by_id else "Sırada"}
    for row in TOC_STATIC
]

STUDY_PHASES = [
    {"Aşama": "1. Konu öğrenme", "Gün": "1-5", "İçerik": "Sayfa sayfa ders, Bölüm 1-4"},
    {"Aşama": "2. Konu + soru", "Gün": "6-7", "İçerik": "Bölüm 5-6 + her bölümden aktif recall"},
    {"Aşama": "3. Yoğun soru çözümü", "Gün": "8-9", "İçerik": "Karışık soru, error log"},
    {"Aşama": "4. Deneme", "Gün": "10", "İçerik": "Tam deneme"},
    {"Aşama": "5. Son tekrar", "Gün": "11", "İçerik": "Sadece error log + mevzuat/süre/oran/kurum, yeni konu yok"},
]

DIAGNOSTIC_QUESTIONS = [
    {"id": 1, "zorluk": "Kolay", "tip": "open", "soru": "Takas ile saklama arasındaki temel fark nedir, tek cümleyle?",
     "model_cevap": "Takas, işlemin karşılıklı yükümlülüklerinin (para↔menkul kıymet) yerine getirilmesi süreci; saklama ise kaydileştirilmiş sermaye piyasası araçlarının merkezi/emanet olarak tutulmasıdır — takas bir an/süreç, saklama süregelen bir durumdur."},
    {"id": 2, "zorluk": "Kolay", "tip": "open", "soru": "MKK'nın açılımı ve temel görevi nedir?",
     "model_cevap": "Merkezi Kayıt Kuruluşu — kaydileştirilen sermaye piyasası araçlarını ve bunlara bağlı hakları elektronik ortamda, üyeler ve hak sahipleri itibarıyla kayden izler, merkezi saklamasını yapar."},
    {"id": 3, "zorluk": "Kolay", "tip": "open", "soru": "Bir hisse alım-satım işleminde 'işlem tarihi' ile 'takas tarihi' arasındaki fark nedir?",
     "model_cevap": "İşlem tarihi (T), alım/satım emrinin borsada eşleştiği tarihtir. Takas tarihi (T+2 gibi), paranın ve hissenin fiilen el değiştirdiği, yükümlülüklerin yerine getirildiği tarihtir — aradaki süre takas riskinin yönetildiği penceredir."},
    {"id": 4, "zorluk": "Orta", "tip": "mc",
     "soru": "Aşağıdakilerden hangisi/hangileri MKK'nın kuruluş amaçlarındandır?\nI. Kaydileştirme işlemlerini gerçekleştirmek\nII. Kaydileştirilen araçları merkezî saklamak\nIII. Piyasa yapıcılığı yapmak",
     "secenekler": ["a) Yalnız I", "b) I ve II", "c) I, II ve III", "d) II ve III", "e) Yalnız III"],
     "dogru": "b) I ve II",
     "kaynak": "Diagnostic soru (PDF'teki gerçek soruya benzer tarzda, III şıkkı MKK'nın görevi olmadığı için eklendi)."},
    {"id": 5, "zorluk": "Orta", "tip": "open", "soru": "Takasbank ile MKK arasındaki rol farkını, 'hangi kurum neyi tutar/hangi kurum neyi garanti eder' ekseninde açıkla.",
     "model_cevap": "MKK, sermaye piyasası araçlarının ve haklarının kaydını tutar (kim, ne kadar sahip). Takasbank ise fiili takas/uzlaşma sürecini yürütür, MKT (merkezi karşı taraf) rolüyle temerrüt riskini üstlenir ve teminat/garanti fonu yönetir — yani MKK 'kayıt', Takasbank 'süreç + risk garantisi'."},
    {"id": 6, "zorluk": "Orta", "tip": "mc", "soru": "Aşağıdakilerden hangisi MKK nezdinde hesap açabilecek kuruluşlardan biri değildir?",
     "secenekler": ["a) Takasbank", "b) Aracı kurumlar", "c) Bankalar", "d) TCMB", "e) TSPB"],
     "dogru": "e) TSPB",
     "kaynak": "PDF Bölüm 2.1, Soru 3 — EK-1 cevap anahtarı."},
    {"id": 7, "zorluk": "Zor", "tip": "open", "soru": "'Başlangıç teminatı' ile 'değişim teminatı' arasındaki fark nedir ve her biri hangi risk senaryosunu karşılar?",
     "model_cevap": "Başlangıç teminatı, pozisyon açılırken ileride oluşabilecek temerrüt riskine karşı baştan alınan teminattır. Değişim teminatı ise pozisyonun günlük piyasa fiyatıyla yeniden değerlenmesi (mark-to-market) sonucu ortaya çıkan farkları karşılamak için ek/eksi olarak talep edilir — başlangıç 'olası' riski, değişim 'gerçekleşen' fiyat hareketini karşılar."},
    {"id": 8, "zorluk": "Zor", "tip": "mc", "soru": "Hakkında tedrici tasfiye kararı verilen bir yatırım kuruluşunun MKK nezdindeki kayıtları üzerinde işlem yapma yetkisi kime devredilir?",
     "secenekler": ["a) MKK", "b) SPK", "c) TCMB", "d) Yatırımcı Tazmin Merkezi (YTM)", "e) Yabancı Merkezi Saklama Kuruluşu (YMSK)"],
     "dogru": "d) Yatırımcı Tazmin Merkezi (YTM)",
     "kaynak": "PDF Bölüm 2.1, Soru 7 — EK-1 cevap anahtarı."},
    {"id": 9, "zorluk": "Senaryo", "tip": "open", "soru": "Bir yatırımcı BIST'te 1000 lot hisse alıyor. İşlem anından parasının/hisselerinin hesabına geçmesine kadar hangi kurumlar sırasıyla devreye girer ve her biri ne yapar?",
     "model_cevap": "1) Aracı kurum emri Borsa İstanbul'a iletir. 2) Borsa İstanbul emri eşleştirir (işlem tarihi/T). 3) Takasbank MKT sıfatıyla devreye girer, alıcıya karşı satıcı/satıcıya karşı alıcı konumuna geçer, teminat/risk yönetimini yapar. 4) Takas günü (T+2) para ve hisse el değiştirir. 5) MKK, hisselerin hak sahibi bazında kayıtlarını günceller."},
    {"id": 10, "zorluk": "Senaryo", "tip": "open", "soru": "Bir aracı kurum, MKT üyesi olarak açık pozisyonunu zamanında kapatamıyor (temerrüt). Bundan sonra hangi mekanizma(lar) devreye girer?",
     "model_cevap": "Önce üyenin yatırdığı teminatlar (başlangıç + değişim) kullanılır. Yetmezse garanti fonu (MKT üyelerinin katkı paylarıyla oluşan fon) devreye girer. Takasbank temerrüt sürecini yönetir, gerekirse pozisyonu piyasada kapatır (likidite eder)."},
    {"id": 11, "zorluk": "Ek", "tip": "open", "soru": "'Açık pozisyon' tanımı hangi piyasalar için geçerlidir (PDF'teki tanıma göre)?",
     "model_cevap": "Borsa İstanbul Vadeli İşlem ve Opsiyon Piyasası ile tezgahüstü vadeli işlem piyasalarında kapatılmamış kısa/uzun pozisyonlar; Ödünç Pay Piyasası'nda ise vadesi gelmemiş menkul kıymet ödünç işlemleri."},
    {"id": 12, "zorluk": "Ek", "tip": "open", "soru": "Garanti fonu ne işe yarar, kim katkı sağlar?",
     "model_cevap": "Merkezi karşı taraf hizmeti verilen piyasalarda takas yükümlülüklerinin yerine getirilmemesi durumunda kullanılır; teminatlar dışında kalan, MKT üyelerinin katkı paylarıyla oluşturulan bir fondur."},
    {"id": 13, "zorluk": "Ek", "tip": "open", "soru": "Borsa İstanbul'un takas sürecindeki rolü nedir — Takasbank'tan farkı ne?",
     "model_cevap": "Borsa İstanbul, alım-satım emirlerinin eşleştiği yerdir (fiyat oluşumu, işlem gerçekleşmesi). Takasbank ise işlem gerçekleştikten sonraki takas/uzlaşma ve risk yönetimi sürecini yürütür — Borsa 'işlem', Takasbank 'sonrası'."},
    {"id": 14, "zorluk": "Ek", "tip": "open", "soru": "Portföy saklama hizmeti kimler tarafından verilebilir, hangi tebliğ düzenliyor?",
     "model_cevap": "III-56.1 Portföy Saklama Hizmetine ve Bu Hizmette Bulunacak Kuruluşlara İlişkin Esaslar Tebliği kapsamında, SPK'dan yetki almış kuruluşlar (ör. Takasbank, bankalar) portföy saklama hizmeti verebilir."},
    {"id": 15, "zorluk": "Ek", "tip": "open", "soru": "Kaydileştirme neden yapılır — hangi problemi çözer (senet basılı sistemine göre)?",
     "model_cevap": "Fiziki senet basımı/saklanması/el değiştirmesinin getirdiği kayıp, sahtecilik, maliyet ve yavaşlık risklerini ortadan kaldırmak için sermaye piyasası araçları elektronik ortamda, senede bağlanmaksızın kayden izlenir."},
]

CATEGORIES = [
    "1. Bilgi eksikliği", "2. Kavram karışıklığı", "3. Kurum karışıklığı", "4. Mevzuat ezberi",
    "5. Süre/oran hatası", "6. Dikkat hatası", "7. Soruyu yanlış okuma", "8. Mantık hatası",
]


def save_error(question_text: str, category: str, note: str) -> None:
    entry = {
        "question": question_text, "category": category, "note": note,
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
    if "spl_error_log" not in st.session_state:
        st.session_state["spl_error_log"] = []
    st.session_state["spl_error_log"].append(entry)
    if client is not None and st.session_state.get("user"):
        try:
            client.table("spl_error_log").insert({**entry, "user_id": st.session_state["user"].id}).execute()
        except Exception as exc:
            bug_tracker.log(exc, context="spl_error_log_save")


tab_plan, tab_diag, tab_lesson, tab_recall, tab_errors, tab_exam = st.tabs(
    ["🗺️ Plan", "📋 Diagnostic Test", "📖 Sayfa Sayfa Ders", "🔁 Aktif Recall", "❌ Error Log", "🎯 Deneme Modu"]
)

with tab_plan:
    st.subheader("Konu Haritası")
    st.table(TOC)
    st.subheader("5 Aşamalı Çalışma Planı (11 gün)")
    st.table(STUDY_PHASES)
    st.caption("Günlük gerçekçi yük ~1,5-2 saat. Son 7 gün kuralı: yeni konu yok, sadece error log + mevzuat/süre/oran/kurum tekrarı.")
    st.info(
        "📰 Güncel bağlantı: Takasbank 15 Eylül 2026'dan itibaren risk parametrelerini güncelledi; "
        "29 Ağustos 2026 tarihli 2167 sayılı Genel Mektup ile MKT prosedürleri değişti — tam olarak "
        "Bölüm 2.3 ve Bölüm 6'nın konusu, sektörde şu an tartışılıyor."
    )

with tab_diag:
    st.subheader("15 Soruluk Diagnostic Test")
    st.caption("Kitap kapalı düşün. Hepsini cevapla, sonra 'Değerlendir'e bas.")

    if "diag_answers" not in st.session_state:
        st.session_state["diag_answers"] = {}

    for q in DIAGNOSTIC_QUESTIONS:
        st.markdown(f"**#{q['id']} [{q['zorluk']}]** {q['soru']}")
        if q["tip"] == "mc":
            st.session_state["diag_answers"][q["id"]] = st.radio(
                "Cevabın:", q["secenekler"], key=f"diag_{q['id']}", index=None
            )
        else:
            st.session_state["diag_answers"][q["id"]] = st.text_area(
                "Cevabın:", key=f"diag_{q['id']}", height=68
            )
        st.markdown("---")

    if st.button("Değerlendir"):
        mc_correct = 0
        mc_total = 0
        for q in DIAGNOSTIC_QUESTIONS:
            ans = st.session_state["diag_answers"].get(q["id"])
            if q["tip"] == "mc":
                mc_total += 1
                is_correct = ans == q["dogru"]
                if is_correct:
                    mc_correct += 1
                    st.success(f"#{q['id']} ✅ Doğru — {q['dogru']}")
                else:
                    st.error(f"#{q['id']} ❌ Yanlış. Doğru cevap: {q['dogru']}")
                    save_error(q["soru"], "Bilinmiyor (senin işaretlemen lazım)", f"Senin cevabın: {ans}")
            else:
                with st.expander(f"#{q['id']} model cevabı ile karşılaştır"):
                    st.write(q["model_cevap"])
        st.metric("Çoktan seçmeli net", f"{mc_correct}/{mc_total}")
        st.caption(
            "Açık uçlu sorular otomatik puanlanmıyor — model cevapla karşılaştır, yanlış/eksikse "
            "aşağıdaki Error Log sekmesinden elle kaydet."
        )

LESSON_FIELD_LABELS = [
    ("konu", "Konu"), ("ana_fikir", "Ana fikir"), ("mevzuat", "Mevzuat"),
    ("mantik", "🧠 MANTIK"), ("ezber", "🔴 EZBER"), ("tuzak", "⚠️ SINAV TUZAĞI"),
    ("gercek_hayat", "Gerçek hayattaki karşılığı"),
]

with tab_lesson:
    st.subheader("Sayfa Sayfa Ders")
    section = st.selectbox("Bölüm seç:", [f"{t['Bölüm']} — {t['Konu']}" for t in TOC])
    bolum_id = section.split(" — ")[0]
    lesson = lessons_by_id.get(bolum_id)

    if lesson is not None and m01["questions"]:
        with st.expander("🔁 Önce hatırla (spaced repetition — yeni konuya geçmeden 2 eski soru)", expanded=False):
            due = m01["questions"]
            if client is not None and st.session_state.get("user"):
                try:
                    stats = (
                        client.table("spl_question_stats")
                        .select("*")
                        .eq("user_id", st.session_state["user"].id)
                        .order("last_seen_at")
                        .limit(2)
                        .execute()
                        .data
                    )
                    seen_ids = {s["question_id"] for s in stats}
                    due = [q for q in m01["questions"] if q["id"] in seen_ids] or m01["questions"][:2]
                except Exception as exc:
                    bug_tracker.log(exc, context="spl_spaced_repetition_fetch")
            for q in due[:2]:
                st.markdown(f"**Soru:** {q['soru']}")
                st.caption(f"Doğru cevap: {q['dogru']}")

    if lesson is None:
        st.info("Bu bölüm henüz işlenmedi — sıradaki adım. 'Bu sayfayı anlat' dediğinde birlikte işleriz.")
    else:
        st.markdown(f"### SAYFA {lesson['sayfa']} — {lesson['baslik']}")
        ders = lesson["ders"]
        for field_key, label in LESSON_FIELD_LABELS:
            if ders.get(field_key):
                st.markdown(f"**{label}:** {ders[field_key]}")

with tab_recall:
    st.subheader("Aktif Recall — PDF kaynaklı gerçek sorular (Bölüm 2.1)")
    st.caption("Kaynak: EK-1 cevap anahtarı. Kitabı kapat, cevapla, sonra kontrol et.")
    for q in m01["questions"]:
        st.markdown(f"**Soru:** {q['soru']}")
        choice = st.radio("Cevabın:", q["secenekler"], key=f"recall_{q['id']}", index=None)
        if st.button("Kontrol et", key=f"recall_btn_{q['id']}"):
            if choice == q["dogru"]:
                st.success("✅ Doğru!")
            else:
                st.error(f"❌ Yanlış. Doğru cevap: {q['dogru']}")
                cat = st.selectbox("Hata kategorisi:", CATEGORIES, key=f"recall_cat_{q['id']}")
                if st.button("Error log'a kaydet", key=f"recall_save_{q['id']}"):
                    save_error(q["soru"], cat, f"Senin cevabın: {choice}")
                    st.toast("Kaydedildi.")
            st.info(q["aciklama"])
        st.markdown("---")

with tab_errors:
    st.subheader("Error Log")
    log = st.session_state.get("spl_error_log", [])
    if not log:
        st.info("Henüz kayıtlı hata yok.")
    else:
        for i, entry in enumerate(reversed(log)):
            st.markdown(f"**{entry['category']}** — {entry['created_at'][:16]}")
            st.caption(entry["question"])
            if entry.get("note"):
                st.caption(entry["note"])
            st.markdown("---")
        from collections import Counter
        counts = Counter(e["category"] for e in log)
        repeated = {k: v for k, v in counts.items() if v > 1}
        if repeated:
            st.warning(f"Tekrar eden hata kategorileri: {repeated} — bu konuları tekrar etmen lazım.")

with tab_exam:
    st.subheader("Deneme Modu")
    st.caption("Tüm soru bankasından (diagnostic + aktif recall) karışık, süreli bir deneme.")

    all_mc = [q for q in DIAGNOSTIC_QUESTIONS if q["tip"] == "mc"] + [
        {"id": f"m01_{q['id']}", "soru": q["soru"], "secenekler": q["secenekler"], "dogru": q["dogru"], "zorluk": "PDF"}
        for q in m01["questions"]
    ]

    if st.button("Yeni deneme başlat"):
        st.session_state["exam_questions"] = random.sample(all_mc, min(8, len(all_mc)))
        st.session_state["exam_start"] = datetime.datetime.now()
        st.session_state["exam_answers"] = {}

    if "exam_questions" in st.session_state:
        elapsed = datetime.datetime.now() - st.session_state["exam_start"]
        st.caption(f"Geçen süre: {int(elapsed.total_seconds() // 60)} dk {int(elapsed.total_seconds() % 60)} sn")
        for q in st.session_state["exam_questions"]:
            st.markdown(f"**[{q['zorluk']}]** {q['soru']}")
            st.session_state["exam_answers"][q["id"]] = st.radio(
                "Cevabın:", q["secenekler"], key=f"exam_{q['id']}", index=None
            )
            st.markdown("---")

        if st.button("Denemeyi bitir"):
            correct = 0
            weak, strong = [], []
            for q in st.session_state["exam_questions"]:
                ans = st.session_state["exam_answers"].get(q["id"])
                if ans == q["dogru"]:
                    correct += 1
                    strong.append(q["soru"][:60])
                else:
                    weak.append(q["soru"][:60])
                    save_error(q["soru"], "Bilinmiyor (senin işaretlemen lazım)", f"Deneme modunda yanlış — cevabın: {ans}")

            total = len(st.session_state["exam_questions"])
            st.metric("Sonuç", f"{correct}/{total}")
            st.markdown("**WEAK TOPIC (zayıf konu):**")
            for w in weak:
                st.write(f"- {w}")
            st.markdown("**STRONG TOPIC (güçlü konu):**")
            for s in strong:
                st.write(f"- {s}")
            st.markdown("**NEXT PRIORITY:** Error Log sekmesindeki tekrar eden kategoriler önceliğin olmalı.")
