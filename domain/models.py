from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List


@dataclass
class MarketState:
    timestamp: str
    inflation: Dict[str, Any]
    tefas_top_funds: List[Dict[str, Any]]
    bist100_liquid: List[Dict[str, Any]]


@dataclass
class ReportInputs:
    report_type: str
    output_type: str
    region: str
    risk_tolerance: str
    investment_capital: float
    sandbox: bool
