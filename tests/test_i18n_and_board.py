"""İki dil katmanı, metrik sözlüğü ve Takım Masası için testler. Çalıştırmak için: python -m pytest tests"""
import json
import string
from pathlib import Path

from utils.i18n import overlay
from utils.team_board import TeamBoard

DATA = Path(__file__).parent.parent / "data"
BASE = json.loads((DATA / "brsan_pitch.json").read_text(encoding="utf-8"))
EN = json.loads((DATA / "i18n" / "brsan_pitch.en.json").read_text(encoding="utf-8"))
GLOSS = json.loads((DATA / "metric_glossary.json").read_text(encoding="utf-8"))

# Cockpit sayfasındaki GV sözlüğünün anahtarları; sözlük metinleri sadece bunları kullanabilir
PAGE_VALUES = {"pe", "ey", "sector_pe", "ev_ebitda_ttm", "ev_ebitda_fwd", "tenaris_fwd", "vallourec_fwd", "nd_ebitda", "lev_2q25",
               "pbv", "bv", "roe", "nm", "at", "em", "wacc", "g", "fcff", "conv", "mc_p50", "mc_prob", "fcf", "cash_conv", "wc",
               "ttm_ebitda", "ttm_ni", "esg50"}


def _lists_align(base, extra, path="root"):
    if isinstance(base, dict) and isinstance(extra, dict):
        for k, v in extra.items():
            assert k in base, f"{path}.{k} İngilizce katmanda var ama Türkçe veride yok"
            _lists_align(base[k], v, f"{path}.{k}")
    elif isinstance(extra, list):
        assert isinstance(base, list) and len(base) == len(extra), f"{path} liste uzunlukları farklı"
        for i, (b, e) in enumerate(zip(base, extra)):
            _lists_align(b, e, f"{path}[{i}]")


def test_english_overlay_matches_base_structure():
    _lists_align(BASE, EN)


def test_overlay_keeps_numbers_and_replaces_text():
    merged = overlay(BASE, EN)
    assert merged["market_snapshot"]["market_cap_mn_usd"] == BASE["market_snapshot"]["market_cap_mn_usd"]
    assert merged["risks"][0]["olasilik"] == BASE["risks"][0]["olasilik"]
    assert merged["risks"][0]["risk"] != BASE["risks"][0]["risk"]
    assert merged["esg"]["ab_gelir_payi"]["deger"] == BASE["esg"]["ab_gelir_payi"]["deger"]


def test_glossary_is_bilingual_and_placeholders_exist():
    fields = {"baslik", "soru", "aciklama", "brsan", "tuzak"}
    for key, entry in GLOSS.items():
        for lang in ("tr", "en"):
            assert set(entry[lang]) == fields, f"{key}/{lang} alanları eksik"
            used = {f for _, f, _, _ in string.Formatter().parse(entry[lang]["brsan"]) if f}
            assert used <= PAGE_VALUES, f"{key}/{lang} bilinmeyen yer tutucu: {used - PAGE_VALUES}"


def test_no_dashes_in_user_facing_text():
    for name in ("brsan_pitch.json", "metric_glossary.json", "i18n/brsan_pitch.en.json"):
        text = (DATA / name).read_text(encoding="utf-8")
        assert "—" not in text and "–" not in text, f"{name} içinde uzun tire var"


def test_team_board_vote_score_and_roundtrip():
    board = TeamBoard()
    board.vote("Selin", "HOLD", 1900, "Marj kalıcı mı?", "ABD yoğunlaşması")
    board.vote("Selin", "BUY", 2100, "Sipariş portföyü", "Marj")
    board.record_score("Selin", 7, 9)
    board.record_score("Selin", 5, 9)
    board.set_member("Selin", "değerleme lideri", ["Valuation", "Financial Analysis"])
    snap = board.snapshot()
    assert snap["votes"]["Selin"]["call"] == "BUY"
    assert snap["scores"]["Selin"] == {**snap["scores"]["Selin"], "last": 5, "best": 7}
    restored = TeamBoard()
    restored.load(json.loads(board.export_json()))
    assert restored.snapshot()["members"] == snap["members"]
    restored.remove_person("Selin")
    assert all("Selin" not in restored.snapshot()[k] for k in ("votes", "members", "scores"))
