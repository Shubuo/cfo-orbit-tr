from __future__ import annotations

from typing import Dict, List

from domain.models import MarketState


def build_missing_notice(missing: List[str]) -> str:
    if not missing:
        return ""
    lines = ["### Veri Eksikleri"]
    for item in missing:
        lines.append(f"- {item}")
    lines.append("Lütfen API erişimlerini ve ağ bağlantısını kontrol edin.")
    lines.append("Sorun sürerse --sandbox ile demo verileri kullanabilirsiniz.")
    return "\n".join(lines)


def build_macro_micro_summary(market: MarketState) -> str:
    cpi = market.inflation.get("cpi", {})
    ppi = market.inflation.get("ppi", {})
    cpi_annual = cpi.get("annual_change") or cpi.get("annual") or cpi.get("current")
    ppi_annual = ppi.get("annual_change") or ppi.get("annual") or ppi.get("current")

    timestamp = market.timestamp or "veri yok"
    macro_lines = [
        "### Makro Özet",
        f"- Veri zamanı: {timestamp}",
        f"- TÜFE (yıllık): {cpi_annual if cpi_annual is not None else 'veri yok'}",
        f"- ÜFE (yıllık): {ppi_annual if ppi_annual is not None else 'veri yok'}",
        "- Enflasyon görünümü yüksek seyrini koruyor; fiyatlama davranışları ve faiz düzeyi belirleyici.",
        "- Reel getiri için vade ve likidite dengesi kritik.",
    ]

    funds = market.tefas_top_funds[:5]
    stocks = market.bist100_liquid[:5]
    fund_list = ", ".join([f"{f.get('fund_code', '')} ({f.get('fund_name', '')})" for f in funds]) or "veri yok"
    stock_list = ", ".join([s.get("symbol", "") for s in stocks]) or "veri yok"

    micro_lines = [
        "### Mikro Özet",
        f"- Öne çıkan TEFAS fonları: {fund_list}",
        f"- Likit BIST100 hisseleri: {stock_list}",
        "- Sektörel ayrışma sürüyor; likidite güçlü hisseler kısa vadede öne çıkıyor.",
        "- Volatiliteye karşı pozisyon boyutları ve stop seviyeleri güncel tutulmalı.",
    ]

    return "\n".join(macro_lines + [""] + micro_lines)


def build_instrument_list(market: MarketState) -> str:
    funds = market.tefas_top_funds[:5]
    stocks = market.bist100_liquid[:5]
    fund_lines = [f"- {f.get('fund_code', '')}: {f.get('fund_name', '')}" for f in funds] or ["- veri yok"]
    stock_lines = [f"- {s.get('symbol', '')}: {s.get('company_name', '')}" for s in stocks] or ["- veri yok"]
    return "\n".join(
        [
            "### Örnek Enstrümanlar",
            "#### TEFAS Fonları",
            *fund_lines,
            "",
            "#### BIST100 Hisseleri",
            *stock_lines,
            "",
            "#### Emtia",
            "- Altın",
            "- Dolar bazlı emtia fonları (varsa)",
        ]
    )
