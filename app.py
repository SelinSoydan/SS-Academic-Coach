import streamlit as st
import datetime
import json
import random

# Sayfa Ayarları
st.set_page_config(page_title="SS Academic Coach", page_icon="🎓", layout="wide")

st.title("🎓 SS Academic Coach")
st.caption("Sermaye Piyasası Lisanslama Sınavları Otomatik Çalışma ve Soru Bankası Motoru")
st.markdown("---")

# 1. OTOMATİK DERS & SAAT PLANLAYICI (SCHEDULER ENGINE)
st.sidebar.header("🗓️ Sınav & Zaman Planlayıcı")

exam_date = st.sidebar.date_input("Yaklaşan SPK Sınav Tarihi", datetime.date(2026, 10, 2))
target_hours = st.sidebar.number_input("Hedef Toplam Çalışma Saati", min_value=10, max_value=200, value=40)

today = datetime.date.today()
days_left = (exam_date - today).days

if days_left > 0:
    daily_needed_hours = round(target_hours / days_left, 1)
    st.sidebar.success(f"⏳ **Kalan Gün:** {days_left} gün")
    st.sidebar.metric("Günde Çalışman Gereken Saat", f"{daily_needed_hours} Saat/Gün")
else:
    st.sidebar.error("⚠️ Sınav günü geldi veya geçti!")

# 2. ÇALIŞMA BİLGİSİ VE DERS ÇIKTILARI
st.header("📌 Aktif SPK Modülleri & Ders Notları")

tab1, tab2 = st.tabs(["📚 Ders Çalışma Çıktıları", "📝 İnteraktif Soru Bankası"])

with open("data/study_plan.json", encoding="utf-8") as f:
    study_data = json.load(f)

with tab1:
    st.subheader("Çalışma Notları ve Özetleri")
    for module in study_data["modules"]:
        st.markdown(f"**{module['title']}:** {module['summary']}")

with tab2:
    st.subheader("🎯 SPK Tarzı Çıkmış & Benzer Sorular")

    for q in study_data["questions"]:
        st.markdown(f"**[{q['modul']}] Soru:** {q['soru']}")
        choice = st.radio(f"Cevabın (Soru {q['id']}):", q['secenekler'], key=f"spk_{q['id']}")
        if st.button(f"Cevabı Onayla #{q['id']}", key=f"spk_btn_{q['id']}"):
            if choice == q['dogru']:
                st.success("✅ DOĞRU!")
            else:
                st.error(f"❌ YANLIŞ. Doğru Cevap: {q['dogru']}")
            st.info(f"💡 **Mevzuat Notu:** {q['aciklama']}")
        st.markdown("---")
