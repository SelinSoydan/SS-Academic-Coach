# SS Academic Coach · Devir notu

Bu dosya, projeyi başka bir Claude hesabından ya da başka bir bilgisayardan devam ettirmek için yazıldı. Yeni oturuma ilk mesaj olarak "HANDOFF.md dosyasını oku ve oradan devam et" demen yeterli.

## Nerede ne var

- Canlı uygulama: https://ss-academic-coach.streamlit.app (GitHub'daki `main` dalına her push otomatik dağıtılır)
- Depo: https://github.com/SelinSoydan/SS-Academic-Coach (public)
- Giriş noktası `app.py`: dil anahtarı (TR/EN) ve `st.navigation` menüsü burada
- `pages/0_Borusan_Equity_Cockpit.py`: CFA Research Challenge analiz masası (8 sekme: tez, değerleme, finansal analiz, risk, ESG, CFA puan haritası, jüri provası, Takım Masası)
- `pages/1_CFA_Research_Challenge.py`: Veri Odası (ham veri, ortaklık, haberler, EquityRT Excel yükleme, 14 şirketlik sektör, rasyo ansiklopedisi)
- `pages/3_SPL_Takas_Saklama_Koc.py`: SPL 1012 modülü koçu, dersler `data/spl_lessons/M01.json` içinde (15 bölüm, tamamı işlendi)
- `pages/2_Matematik_Programi.py`: Finansal Modelleme Defteri
- `utils/valuation.py`: bütün değerleme formülleri, Streamlit'ten bağımsız ve birim testli
- `utils/i18n.py`: dil yardımcıları; İngilizce metinler `data/i18n/brsan_pitch.en.json` içinde, sayılar tek kaynakta
- `utils/team_board.py`: Takım Masası'nın ortak canlı panosu (sunucu belleğinde, uygulama yeniden başlarsa sıfırlanır, JSON yedeği alınabilir)
- `data/brsan_pitch.json`: Borusan verisi, her rakam kaynağıyla (1Ç26 ve 2Ç26 yatırımcı sunumları, EquityRT 22.09.2026)
- `data/metric_glossary.json`: 14 metriğin iki dilli sezgisel açıklaması
- `data/cfa_peers.json`: dar peer grubu (Tenaris, Vallourec) ve geniş sektör listesi

## Testler

```
python -m pytest tests
```

15 test: formüller, F/K mutabakatı, çeyreklerin yarıyıla toplanması, İngilizce katmanın yapısı, sözlükteki yer tutucular, metinlerde uzun tire olmaması, Takım Masası.

## Çalışma kuralları (Selin'in kararları)

- Kaynağı gösterilemeyen hiçbir rakam uygulamaya girmez; eksik veri "yok" diye işaretlenir, tahminle doldurulmaz.
- Metinler akıcı ve öğretici Türkçe; uzun tire ve yapay zekâ kokan dil yok.
- Hedef şirket Borusan Boru (BRSAN), Borusan Holding değil. Borusan EnBW Enerji ve Borusan Yatırım ve Pazarlama başka şirketler.
- SPL kitabındaki soruların aynen metni telifli; bu public depoya konmaz.
- Veri güncellemesi kod değil JSON değişikliğidir: yeni çeyrekte `data/brsan_pitch.json` içindeki `donemler`, `ttm_bazi` ve `net_borc_donemi` güncellenir, bütün sayfa kendini yeniden hesaplar.

## Açık işler (öncelik sırasıyla)

1. ROIC: yatırılan sermaye KAP bilançosundan eklenecek, WACC ile yan yana konacak.
2. WACC'ı kaynaklı kurmak (risksiz faiz, beta, ülke risk primi); şu an slider varsayımı.
3. Dar peer grubunu 5 ile 10 şirkete çıkarmak (Jindal SAW ve benzerleri, EquityRT'den).
4. Firma değerine azınlık payları ve kiralama yükümlülüklerini eklemek.
5. ESG sayısal verileri: TSRS raporunun tam metninden emisyon yoğunluğu, enerji, iş kazası oranı; AB gelir payını (%15) PDF'ten teyit etmek.
6. Takım Masası'nı kalıcı hale getirmek: Supabase projesi açılıp anahtarlar Streamlit Cloud ayarlarına girilince `utils/team_board.py` aynı arayüzle tabloya yazacak şekilde değiştirilir.
7. Maliyet yapısı varsayımlarını (girdi çeliğin gelire oranı, fiyat geçişkenliği) faaliyet raporundan gerçek veriye çevirmek.
