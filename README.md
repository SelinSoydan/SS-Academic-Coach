# SS Academic Coach

SPK lisanslama sınavlarına hazırlık için Streamlit tabanlı çalışma koçu. Sadece resmi SPL modüllerinden gelen içerik kullanır; mevzuat/tebliğ güncellemelerini günlük olarak tarar.

## Kurulum

1. [Supabase](https://supabase.com) üzerinde ücretsiz bir proje oluştur.
2. Supabase SQL editöründe şu tabloları oluştur:

```sql
create table regulatory_updates (
  id bigint generated always as identity primary key,
  title text not null,
  source text not null,
  source_url text not null,
  detected_at timestamptz not null default now()
);

create table bug_reports (
  id bigint generated always as identity primary key,
  timestamp timestamptz not null,
  context text not null,
  severity text not null,
  message text,
  traceback text
);
```

3. Proje ayarlarından `Project URL` ve `anon public key`'i al.
4. Yerelde çalıştırmak için `.env` dosyası oluştur (`.env.example`'ı kopyala) veya `.streamlit/secrets.toml` içine:

```toml
SUPABASE_URL = "https://xxxx.supabase.co"
SUPABASE_KEY = "..."
```

5. Bağımlılıkları kur ve çalıştır:

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Günlük mevzuat taraması

`scripts/regulatory_watcher.py` SPK duyurular sayfası ve Resmi Gazete'yi tarar, yeni başlıkları `regulatory_updates` tablosuna ekler. Günde bir kez otomatik çalıştırmak için bir cron/scheduled task olarak kur (Streamlit Cloud arka planda script çalıştırmaz, bu yüzden GitHub Actions cron veya benzeri bir dış tetikleyici gerekir):

```bash
python scripts/regulatory_watcher.py
```

## Resmi SPL modülleri

`data/official_spk_modules.json` şu an 12 boş modül (M01–M12) içeriyor. İçerik yalnızca Selin'in sağladığı resmi SPL ders materyallerinden doldurulur — internetten toplanan doğrulanamayan sorular kullanılmaz.

## Hata takibi

`utils/bug_tracker.py` içindeki `BugTracker` sınıfı hataları `logs/error_tracker.json` dosyasına (ve varsa Supabase `bug_reports` tablosuna) kaydeder.
