from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from crewai.tools import tool
except Exception:  # Fallback to keep module importable if crewai is missing
    def tool(*_args: Any, **_kwargs: Any):  # type: ignore
        def decorator(func: Any) -> Any:
            return func

        return decorator


def _safe_to_records(data: Any) -> Any:
    """Convert pandas-like objects to plain JSON-serializable structures."""
    try:
        if hasattr(data, "to_dict"):
            return data.to_dict(orient="records")  # type: ignore[arg-type]
    except Exception:
        pass
    return data


def _now_iso() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

def _sandbox_enabled() -> bool:
    return os.getenv("SANDBOX_MODE", "false").lower() == "true"


def _load_sandbox_json(name: str) -> Optional[Dict[str, Any]]:
    if not _sandbox_enabled():
        return None
    path = Path("data") / "sandbox" / f"{name}.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


@tool("fetch_tuik_inflation")
def fetch_tuik_inflation() -> str:
    """Fetch latest CPI/PPI inflation from TUIK via borsapy."""
    try:
        sandbox = _load_sandbox_json("tuik")
        if sandbox:
            return json.dumps(sandbox, ensure_ascii=False)
        import borsapy  # type: ignore

        data: Dict[str, Any] = {"source": "borsapy", "timestamp": _now_iso()}

        if hasattr(borsapy, "TUIK"):
            tuik = borsapy.TUIK()
            # Attempt common method names
            if hasattr(tuik, "inflation"):
                data["inflation"] = _safe_to_records(tuik.inflation())
            elif hasattr(tuik, "inflation_cpi"):
                data["cpi"] = _safe_to_records(tuik.inflation_cpi())
            elif hasattr(tuik, "inflation_ppi"):
                data["ppi"] = _safe_to_records(tuik.inflation_ppi())
        elif hasattr(borsapy, "tuik_inflation"):
            data["inflation"] = _safe_to_records(borsapy.tuik_inflation())
        else:
            data["error"] = "borsapy TUIK interface not found"

        return json.dumps(data, ensure_ascii=False)
    except Exception as exc:
        return json.dumps(
            {"error": "tuik_inflation_failed", "details": str(exc)},
            ensure_ascii=False,
        )


@tool("fetch_top_tefas_funds")
def fetch_top_tefas_funds(limit: int = 5) -> str:
    """Fetch top-performing TEFAS funds via tefasfon."""
    try:
        sandbox = _load_sandbox_json("tefas")
        if sandbox:
            return json.dumps(sandbox, ensure_ascii=False)
        import tefasfon  # type: ignore

        data: Dict[str, Any] = {"source": "tefasfon", "timestamp": _now_iso()}
        funds: Any = None

        # Attempt common entry points
        if hasattr(tefasfon, "TefasFon"):
            tf = tefasfon.TefasFon()
            if hasattr(tf, "get_fund_list"):
                funds = tf.get_fund_list()
            elif hasattr(tf, "fund_list"):
                funds = tf.fund_list()
        elif hasattr(tefasfon, "get_fund_list"):
            funds = tefasfon.get_fund_list()

        if funds is None:
            data["error"] = "tefasfon fund list not available"
            return json.dumps(data, ensure_ascii=False)

        funds = _safe_to_records(funds)

        # Heuristic: select top funds by 1Y/6M return fields if present
        def _score(item: Dict[str, Any]) -> float:
            for key in ("return_1y", "return_6m", "getiri_1y", "getiri_6ay"):
                if key in item and isinstance(item[key], (int, float)):
                    return float(item[key])
            return 0.0

        if isinstance(funds, list):
            funds_sorted = sorted(
                [f for f in funds if isinstance(f, dict)],
                key=_score,
                reverse=True,
            )
            data["top_funds"] = funds_sorted[: max(1, int(limit))]
        else:
            data["top_funds"] = funds

        return json.dumps(data, ensure_ascii=False)
    except Exception as exc:
        return json.dumps(
            {"error": "tefas_funds_failed", "details": str(exc)},
            ensure_ascii=False,
        )


@tool("fetch_liquid_bist100_stocks")
def fetch_liquid_bist100_stocks(limit: int = 10) -> str:
    """Fetch highly liquid BIST 100 stocks using borsapy."""
    try:
        sandbox = _load_sandbox_json("bist100")
        if sandbox:
            return json.dumps(sandbox, ensure_ascii=False)
        import borsapy  # type: ignore

        data: Dict[str, Any] = {"source": "borsapy", "timestamp": _now_iso()}
        stocks: Any = None

        if hasattr(borsapy, "Borsa"):
            borsa = borsapy.Borsa()
            # Attempt common method names
            if hasattr(borsa, "get_stocks"):
                stocks = borsa.get_stocks("XU100")
            elif hasattr(borsa, "get_market"):
                stocks = borsa.get_market("XU100")
            elif hasattr(borsa, "bist100"):
                stocks = borsa.bist100()
        elif hasattr(borsapy, "bist100"):
            stocks = borsapy.bist100()

        if stocks is None:
            data["error"] = "borsapy BIST 100 interface not found"
            return json.dumps(data, ensure_ascii=False)

        stocks = _safe_to_records(stocks)

        def _volume_score(item: Dict[str, Any]) -> float:
            for key in ("volume", "hacim", "vol"):
                if key in item and isinstance(item[key], (int, float)):
                    return float(item[key])
            return 0.0

        if isinstance(stocks, list):
            stocks_sorted = sorted(
                [s for s in stocks if isinstance(s, dict)],
                key=_volume_score,
                reverse=True,
            )
            data["liquid_stocks"] = stocks_sorted[: max(1, int(limit))]
        else:
            data["liquid_stocks"] = stocks

        return json.dumps(data, ensure_ascii=False)
    except Exception as exc:
        return json.dumps(
            {"error": "bist100_liquidity_failed", "details": str(exc)},
            ensure_ascii=False,
        )


@tool("draw_portfolio_pie")
def draw_portfolio_pie(allocation_json: str) -> str:
    """Draw a portfolio pie chart in the terminal using plotext."""
    try:
        import plotext as plt  # type: ignore

        allocation = json.loads(allocation_json)
        if not isinstance(allocation, dict):
            return "allocation_json is not a JSON object"

        labels: List[str] = []
        values: List[float] = []
        for key, value in allocation.items():
            if isinstance(value, (int, float)):
                labels.append(str(key))
                values.append(float(value))

        if not labels:
            return "no numeric allocation values found"

        plt.clear_figure()
        plt.pie(values, labels=labels)
        plt.title("Portfoy Dagilimi")
        plt.show()
        return "pie_chart_drawn"
    except Exception as exc:
        return f"pie_chart_failed: {exc}"
