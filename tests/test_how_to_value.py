import json
from pathlib import Path

BASE = Path(__file__).parent.parent / "data" / "how_to_value"
DATA = json.loads((BASE / "content.json").read_text(encoding="utf-8"))


def test_content_shape():
    assert [s["n"] for s in DATA["slides"]] == list(range(1, 13))
    assert len(DATA["questions"]) == 16
    for s in DATA["slides"]:
        assert s["learn"] and s["tr"] and s["en"], s["n"]
        assert (BASE / s["image"]).exists()
    assert (BASE / DATA["meta"]["deck"]).exists()


def test_speaking_scripts_fit_the_time_limit_and_have_no_dashes():
    words = sum(len(s["en"].split()) for s in DATA["slides"])
    assert words <= 850  # about 6 minutes at a normal pace
    for s in DATA["slides"]:
        for field in ("en", "tr"):
            assert "—" not in s[field] and "–" not in s[field], (s["n"], field)


def test_numbers_match_the_valuation_story():
    n = DATA["numbers"]
    assert n["wacc_us"] < n["wacc_blend"] < n["wacc_tr"]
    assert n["eq_bear"] < n["eq_base"] < n["eq_bull"]
