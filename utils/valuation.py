"""Borusan pitch sayfasının hesap çekirdeği.

Saf Python, Streamlit'e bağımlı değil; böylece her formül tests/test_valuation.py
içinde tek başına doğrulanabiliyor. Tüm tutarlar aynı para biriminde (mn $) girilir.
"""


def ttm(full_year: float, prev_year_quarter: float, this_year_quarter: float) -> float:
    """Son on iki ay: yıllık rakam, geçen yılın aynı çeyreği çıkar, bu yılın çeyreği eklenir."""
    return full_year - prev_year_quarter + this_year_quarter


def growth(new: float, old: float) -> float:
    if old <= 0:
        raise ValueError("Baz değer sıfır ya da negatif; zarardan kâra geçişte yüzde büyüme anlamsız.")
    return new / old - 1


def enterprise_value(market_cap: float, net_debt: float) -> float:
    return market_cap + net_debt


def equity_from_ev_multiple(multiple: float, ebitda: float, net_debt: float) -> float:
    """Çarpan x FAVÖK = firma değeri; net borç düşülünce özsermaye değeri kalır."""
    return multiple * ebitda - net_debt


def equity_from_relative_multiple(market_cap: float, own_multiple: float, peer_multiple: float) -> float:
    """F/K ve PD/DD gibi özsermaye çarpanlarında: şirket peer çarpanından işlem görseydi değeri ne olurdu."""
    if own_multiple <= 0:
        raise ValueError("Şirketin kendi çarpanı pozitif olmalı.")
    return market_cap * peer_multiple / own_multiple


def implied_steady_fcff(ev: float, wacc: float, g: float) -> float:
    """Reverse DCF: bugünkü firma değerini haklı çıkaran, sonsuza büyüyen ilk yıl serbest nakit akımı.

    Gordon formülü EV = FCFF1 / (WACC - g) tersine çevrilir, FCFF1 = FCFF0 x (1 + g) olduğundan
    FCFF0 = EV x (WACC - g) / (1 + g).
    """
    if wacc <= g:
        raise ValueError("WACC büyüme oranından büyük olmalı, yoksa formül anlamsızlaşır.")
    return ev * (wacc - g) / (1 + g)


def ev_from_fcff(fcff0: float, wacc: float, g: float) -> float:
    """Gordon büyüme modeli: EV = FCFF0 x (1 + g) / (WACC - g). implied_steady_fcff'in tersi."""
    if wacc <= g:
        raise ValueError("WACC büyüme oranından büyük olmalı.")
    return fcff0 * (1 + g) / (wacc - g)


def dupont(net_income: float, revenue: float, assets: float, equity: float) -> dict:
    """ROE'yi net marj, aktif devir hızı ve finansal kaldıraç çarpımına ayırır."""
    margin, turnover, leverage = net_income / revenue, revenue / assets, assets / equity
    return {"net_marj": margin, "aktif_devir": turnover, "kaldirac": leverage, "roe": margin * turnover * leverage}


def upside(implied: float, current: float) -> float:
    return implied / current - 1


def guidance_ebitda(revenue: float, margin: float) -> float:
    return revenue * margin


def net_debt_to_ebitda(net_debt: float, ebitda: float) -> float:
    if ebitda <= 0:
        raise ValueError("FAVÖK pozitif olmalı.")
    return net_debt / ebitda
