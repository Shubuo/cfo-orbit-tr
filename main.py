from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path
from getpass import getpass
from typing import Any, Dict, Optional, Tuple, TypedDict

from crewai import Crew, Process
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI

from agents import create_agents
from tasks import create_tasks
from tools import draw_portfolio_pie


class ReportPayload(TypedDict, total=False):
    report_markdown: str
    terminal_summary: str
    portfolio_allocation: Dict[str, float]
    data_health: str


def _prompt_api_key() -> str:
    api_key = getpass("GEMINI_API_KEY (gizli): ").strip()
    if not api_key:
        raise ValueError("GEMINI_API_KEY bos olamaz.")
    return api_key


def _prompt_risk_tolerance() -> str:
    mapping = {
        "low": "Low",
        "medium": "Medium",
        "high": "High",
        "dusuk": "Low",
        "düşük": "Low",
        "orta": "Medium",
        "yuksek": "High",
        "yüksek": "High",
    }
    while True:
        value = input("Risk Toleransi (Low/Medium/High): ").strip().lower()
        if value in mapping:
            return mapping[value]
        print("Gecersiz giris. Lutfen Low/Medium/High girin.")


def _prompt_capital() -> float:
    while True:
        raw = input("Yatirim Sermayesi (TL): ").strip().replace(",", "")
        try:
            value = float(raw)
            if value <= 0:
                raise ValueError("capital must be positive")
            return value
        except Exception:
            print("Gecersiz tutar. Ornek: 250000")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Personal CFO CLI")
    parser.add_argument(
        "--non-interactive",
        action="store_true",
        help="Non-interactive mode (requires env vars).",
    )
    parser.add_argument("--risk", type=str, default="")
    parser.add_argument("--capital", type=str, default="")
    return parser.parse_args()


def _extract_json(text: str) -> Optional[Dict[str, Any]]:
    text = text.strip()
    if text.startswith("{") and text.endswith("}"):
        try:
            return json.loads(text)
        except Exception:
            return None
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group(0))
    except Exception:
        return None


def _log_raw_output(raw: str) -> None:
    Path("logs").mkdir(exist_ok=True)
    with open("logs/raw_report.txt", "w", encoding="utf-8") as f:
        f.write(raw)


def _validate_report_payload(data: Dict[str, Any]) -> ReportPayload:
    payload: ReportPayload = {}
    if isinstance(data.get("report_markdown"), str):
        payload["report_markdown"] = data["report_markdown"].strip()
    if isinstance(data.get("terminal_summary"), str):
        payload["terminal_summary"] = data["terminal_summary"].strip()
    if isinstance(data.get("portfolio_allocation"), dict):
        allocation = {
            str(k): float(v)
            for k, v in data["portfolio_allocation"].items()
            if isinstance(v, (int, float))
        }
        if allocation:
            payload["portfolio_allocation"] = allocation
    if isinstance(data.get("data_health"), str):
        payload["data_health"] = data["data_health"].strip()
    return payload


def _parse_report_output(raw: str) -> Tuple[str, str, Optional[Dict[str, float]]]:
    data = _extract_json(raw)
    if not data:
        _log_raw_output(raw)
        return "", "", None
    payload = _validate_report_payload(data)
    report_md = payload.get("report_markdown", "")
    summary = payload.get("terminal_summary", "")
    allocation = payload.get("portfolio_allocation")
    return report_md, summary, allocation


def _normalize_allocation(allocation: Dict[str, float]) -> Dict[str, float]:
    cleaned = {k: max(0.0, float(v)) for k, v in allocation.items()}
    total = sum(cleaned.values())
    if total <= 0:
        return {}
    return {k: round((v / total) * 100.0, 2) for k, v in cleaned.items()}


def _validate_allocation(allocation: Dict[str, float]) -> bool:
    if not allocation:
        return False
    total = sum(allocation.values())
    return 98.0 <= total <= 102.0 and all(v >= 0 for v in allocation.values())


def main() -> None:
    args = _parse_args()
    load_dotenv()

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        if args.non_interactive:
            print("GEMINI_API_KEY bulunamadi. Non-interactive modda .env gerekli.")
            return
        api_key = _prompt_api_key()
        os.environ["GEMINI_API_KEY"] = api_key

    if args.non_interactive:
        risk_tolerance = (args.risk or os.getenv("RISK_TOLERANCE", "")).strip()
        capital_raw = (args.capital or os.getenv("INVESTMENT_CAPITAL", "")).strip()
        if not risk_tolerance or not capital_raw:
            print("Non-interactive mod icin RISK_TOLERANCE ve INVESTMENT_CAPITAL gerekli.")
            return
        try:
            investment_capital = float(capital_raw)
        except Exception:
            print("INVESTMENT_CAPITAL sayi olmali.")
            return
    else:
        risk_tolerance = _prompt_risk_tolerance()
        investment_capital = _prompt_capital()

    llm_flash = ChatGoogleGenerativeAI(
        model="gemini-1.5-flash",
        temperature=0.2,
        google_api_key=api_key,
    )
    llm_pro = ChatGoogleGenerativeAI(
        model="gemini-1.5-pro",
        temperature=0.2,
        google_api_key=api_key,
    )

    agents = create_agents(llm_pro=llm_pro, llm_flash=llm_flash)
    tasks = create_tasks(
        agents=agents,
        risk_tolerance=risk_tolerance,
        investment_capital=investment_capital,
    )

    crew = Crew(
        agents=list(agents.values()),
        tasks=tasks,
        process=Process.sequential,
        verbose=True,
    )

    try:
        result = crew.kickoff()
    except Exception as exc:
        print(f"Calistirma hatasi: {exc}")
        return

    raw_output = str(result)
    report_md, summary, allocation = _parse_report_output(raw_output)

    if not report_md:
        print("Rapor JSON formatinda uretilmedi. Ham cikti logs/raw_report.txt dosyasinda.")
        return

    if report_md:
        with open("monthly_cfo_report.md", "w", encoding="utf-8") as f:
            f.write(report_md)

    if allocation:
        normalized = _normalize_allocation(allocation)
        if _validate_allocation(normalized):
            draw_portfolio_pie(json.dumps(normalized, ensure_ascii=False))

    if summary:
        print("\n--- Ozet ---")
        print(summary)
    else:
        print("\nRapor olusturuldu: monthly_cfo_report.md")


if __name__ == "__main__":
    main()
