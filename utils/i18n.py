"""İki dilli arayüz (TR/EN) için küçük yardımcılar.

Dil seçimi st.session_state["lang"] içinde tutulur. Veri dosyalarının İngilizcesi ayrı bir
"overlay" JSON'da durur; sayılar tek kaynakta (Türkçe dosyada) kalır, overlay sadece metni değiştirir.
"""
import json
from pathlib import Path

import streamlit as st

DATA = Path(__file__).parent.parent / "data"


def lang() -> str:
    return st.session_state.get("lang", "TR")


def is_en() -> bool:
    return lang() == "EN"


def L(tr: str, en: str) -> str:
    return en if is_en() else tr


def overlay(base, extra):
    """extra'daki metinleri base'in üstüne yazar. Sözlükler anahtarla, listeler sırayla birleşir."""
    if isinstance(base, dict) and isinstance(extra, dict):
        out = dict(base)
        for k, v in extra.items():
            out[k] = overlay(base[k], v) if k in base else v
        return out
    if isinstance(base, list) and isinstance(extra, list):
        return [overlay(b, extra[i]) if i < len(extra) else b for i, b in enumerate(base)]
    return base if extra is None else extra


def load_localized(name: str) -> dict:
    """data/<name> dosyasını yükler; EN seçiliyse data/i18n/<stem>.en.json overlay'ini uygular."""
    base = json.loads((DATA / name).read_text(encoding="utf-8"))
    if not is_en():
        return base
    en_path = DATA / "i18n" / f"{Path(name).stem}.en.json"
    if not en_path.exists():
        return base
    return overlay(base, json.loads(en_path.read_text(encoding="utf-8")))


class _Blank(dict):
    def __missing__(self, key):
        return "?"


def fill(template: str, values: dict) -> str:
    """Sözlük metnindeki {pe} gibi yer tutucuları o anki hesaplanmış değerlerle doldurur."""
    return template.format_map(_Blank(values))


def num(x: float, d: int = 1) -> str:
    """Dile göre sayı biçimi: TR 1.917,9 / EN 1,917.9"""
    s = f"{x:,.{d}f}"
    return s if is_en() else s.replace(",", "§").replace(".", ",").replace("§", ".")


def pp(x_percent: float, d: int = 1) -> str:
    """Zaten yüzde cinsinden bir sayıyı biçimler: TR %12,5 / EN 12.5%"""
    sign, body = ("-" if x_percent < 0 else ""), num(abs(x_percent), d)
    return f"{sign}{body}%" if is_en() else f"{sign}%{body}"


def period(key: str) -> str:
    """Dönem etiketleri: TR 1Ç26 / 1Y26, EN 1Q26 / 1H26"""
    return key.replace("Ç", "Q").replace("Y", "H") if is_en() else key
