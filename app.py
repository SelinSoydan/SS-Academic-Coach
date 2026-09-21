import datetime
import json
from pathlib import Path

import streamlit as st

from utils.auth import render_login_gate, sign_out
from utils.bug_tracker import BugTracker
from utils.supabase_client import get_supabase_client

st.set_page_config(page_title="SS Academic Coach", page_icon="🎓", layout="wide")

client = get_supabase_client()
bug_tracker = BugTracker(supabase_client=client)

if client is None:
    st.warning(
        "Supabase bağlantısı yapılandırılmamış (SUPABASE_URL / SUPABASE_KEY). "
        "Giriş/kayıt devre dışı; sadece genel görünüm gösteriliyor."
    )
else:
    if not render_login_gate(client, bug_tracker):
        st.stop()

MODULES_PATH = Path(__file__).parent / "data" / "official_spk_modules.json"

try:
    modules_data = json.loads(MODULES_PATH.read_text(encoding="utf-8"))
except Exception as exc:
    bug_tracker.log(exc, context="load_official_spk_modules")
    st.error("Modül verisi okunamadı. logs/error_tracker.json içine kaydedildi.")
    st.stop()

st.title("🎓 SS Academic Coach")
st.caption("Sermaye Piyasası Lisanslama Sınavları — resmi SPL modülleri ve güncel mevzuat")

if client is not None and st.session_state.get("user"):
    with st.sidebar:
        st.write(f"👤 {st.session_state['user'].email}")
        if st.button("Çıkış Yap"):
            sign_out(client)
            st.rerun()

st.sidebar.markdown("---")
st.sidebar.header("🗓️ Dynamic SPK Scheduler")

exam_date = st.sidebar.date_input("Yaklaşan SPK Sınav Tarihi", datetime.date(2026, 10, 2))
target_hours = st.sidebar.number_input("Hedef Toplam Çalışma Saati", min_value=10, max_value=200, value=40)

today = datetime.date.today()
days_left = (exam_date - today).days

if days_left > 0:
    daily_needed_hours = round(target_hours / days_left, 1)
    st.sidebar.success(f"⏳ Kalan Gün: {days_left} gün")
    st.sidebar.metric("Günde Çalışman Gereken Saat", f"{daily_needed_hours} Saat/Gün")
else:
    st.sidebar.error("⚠️ Sınav günü geldi veya geçti!")

tab_modules, tab_regulatory = st.tabs(
    ["📚 Official SPL Module & Communiqué Exam Engine", "🔗 Real-World Case & KAP Linkage"]
)

with tab_modules:
    st.subheader("Resmi SPL Modülleri")
    missing = [m for m in modules_data["modules"] if not m["title"]]
    if missing:
        st.info(
            f"{len(missing)}/12 modül henüz boş. Selin'in gönderdiği resmi SPL ders "
            "materyalleri eklendiğinde bu alan gerçek modül adı, tebliğ referansları ve "
            "sorularla dolacak — içerik doğrulanmadan üretilmez."
        )
    for module in modules_data["modules"]:
        title = module["title"] or f"({module['module_id']} — kaynak bekleniyor)"
        with st.expander(f"{module['module_id']} · {title}"):
            if not module["title"]:
                st.caption("Bu modül için henüz resmi SPL kaynağı yüklenmedi.")
                continue
            st.write(f"Kaynak: {module['spl_source_ref']}")
            for comm in module["related_communiques"]:
                st.markdown(f"- **{comm['code']}** {comm['name']}")
            for q in module["questions"]:
                st.markdown(f"**Soru:** {q['soru']}")
                choice = st.radio("Cevabın:", q["secenekler"], key=f"q_{module['module_id']}_{q['id']}")
                if st.button("Cevabı Onayla", key=f"btn_{module['module_id']}_{q['id']}"):
                    if choice == q["dogru"]:
                        st.success("✅ Doğru!")
                    else:
                        st.error(f"❌ Yanlış. Doğru cevap: {q['dogru']}")
                    st.info(q["aciklama"])

with tab_regulatory:
    st.subheader("Mevzuatın BIST/Rasyonet/KAP Pratikleriyle Bağlantısı")
    linked = [m for m in modules_data["modules"] if m["real_world_links"]]
    if not linked:
        st.info(
            "Gerçek hayat bağlantıları (BIST işlemleri, Rasyonet veri analitiği, KAP bildirimleri) "
            "modül kaynakları eklendikçe burada listelenecek."
        )
    for module in linked:
        st.markdown(f"**{module['module_id']} · {module['title']}**")
        for link in module["real_world_links"]:
            st.markdown(f"- *{link['context']}*: {link['note']}")

    st.markdown("---")
    st.subheader("📡 Mevzuat Güncelleme Takibi")
    last_checked = modules_data["regulatory_watch"]["last_checked"]
    st.write(f"Son kontrol: {last_checked or 'Henüz çalıştırılmadı'}")
    st.caption(
        "Günlük otomatik tarama `scripts/regulatory_watcher.py` ile SPK duyurular sayfası "
        "ve Resmi Gazete'yi kontrol eder; sonuçlar Supabase `regulatory_updates` tablosuna yazılır."
    )
    if client is not None:
        try:
            updates = (
                client.table("regulatory_updates")
                .select("*")
                .order("detected_at", desc=True)
                .limit(20)
                .execute()
                .data
            )
            if updates:
                for u in updates:
                    st.markdown(f"- [{u['title']}]({u['source_url']}) — {u['source']} · {u['detected_at']}")
            else:
                st.caption("Henüz kayıtlı güncelleme yok.")
        except Exception as exc:
            bug_tracker.log(exc, context="render_regulatory_updates")
            st.error("Güncellemeler yüklenemedi.")
