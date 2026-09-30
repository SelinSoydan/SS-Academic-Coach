"""Hesap çekirdeğinin birim testleri. Çalıştırmak için: python -m pytest tests"""
import json
import math
from pathlib import Path

import pytest

from utils import valuation as v

PITCH = json.loads((Path(__file__).parent.parent / "data" / "brsan_pitch.json").read_text(encoding="utf-8"))
P = PITCH["financials"]["donemler"]


def test_ttm_ebitda_matches_hand_calculation():
    # 2025 FAVÖK 133,1 eksi 1Y25 53,5 artı 1Y26 90,3
    assert math.isclose(v.ttm(P["2025"]["favok"], P["1Y25"]["favok"], P["1Y26"]["favok"]), 169.9, abs_tol=1e-9)


def test_pe_reconciles_with_equityrt():
    """EquityRT'deki F/K, piyasa değerinin USD bazlı son 12 ay net kâra bölümüyle tutmalı."""
    ttm_ni = v.ttm(P["2025"]["net_kar"], P["1Y25"]["net_kar"], P["1Y26"]["net_kar"])
    implied_pe = PITCH["market_snapshot"]["market_cap_mn_usd"] / ttm_ni
    assert abs(implied_pe - PITCH["market_snapshot"]["p_e"]) < 0.01


def test_quarters_add_up_to_half_year():
    for k in ("gelir", "favok", "net_kar"):
        assert math.isclose(P["1Ç26"][k] + P["2Ç26"][k], P["1Y26"][k], abs_tol=0.15)
        assert math.isclose(P["1Ç25"][k] + P["2Ç25"][k], P["1Y25"][k], abs_tol=0.15)


def test_reverse_dcf_round_trip():
    ev, wacc, g = 2061.91, 0.11, 0.025
    fcff0 = v.implied_steady_fcff(ev, wacc, g)
    assert math.isclose(fcff0 * (1 + g) / (wacc - g), ev, rel_tol=1e-12)


def test_reverse_dcf_rejects_wacc_below_growth():
    with pytest.raises(ValueError):
        v.implied_steady_fcff(1000, 0.03, 0.03)


def test_ev_multiple_to_equity():
    assert v.equity_from_ev_multiple(10, 200, 144) == 1856


def test_relative_multiple_scales_market_cap():
    assert math.isclose(v.equity_from_relative_multiple(1000, 20, 10), 500)
    with pytest.raises(ValueError):
        v.equity_from_relative_multiple(1000, 0, 10)


def test_growth_rejects_loss_base():
    with pytest.raises(ValueError):
        v.growth(31.7, -5.1)
    assert math.isclose(v.growth(110, 100), 0.10)
