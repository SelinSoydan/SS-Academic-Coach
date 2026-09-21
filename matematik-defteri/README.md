# Finansal Modelleme Defteri

Ders ders büyüyen, tek sayfalık interaktif matematik/ekonometri öğretmeni. Log & türev, Σ/varyans/kovaryans, doğrusal regresyon tekrarından başlayıp yüksek lisans (AI x Finans) hazırlığı için gereken matematiği sıfırdan işliyor.

Canlı: bkz. GitHub Pages linki (repo Settings → Pages).

## Yapı

Tek dosya: `index.html`. Yeni ders eklerken:
1. `<nav class="toc">` içine yeni derse link ekle.
2. `<div class="chapter" id="dersN">` bloğu olarak yeni dersi ekle — section id'leri o dersin içinde tekil olmalı (ör. `dN-0`, `dN-1`).
3. Yayınlamadan önce `<script>` içeriğini `node --check` ile syntax kontrolünden geçir.
