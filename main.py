from __future__ import annotations

import json
import os
import re
from getpass import getpass
from typing import Any, Dict, Optional, Tuple

from crewai import Crew, Process
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI

from agents import create_agents
from tasks import create_tasks
from tools import draw_portfolio_pie


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


def _parse_report_output(raw: str) -> Tuple[str, str, Optional[Dict[str, Any]]]:
    data = _extract_json(raw)
    if not data:
        return raw, "", None
    report_md = str(data.get("report_markdown", "")).strip()
    summary = str(data.get("terminal_summary", "")).strip()
    allocation = data.get("portfolio_allocation")
    if isinstance(allocation, dict):
        return report_md, summary, allocation
    return report_md, summary, None


def main() -> None:
    load_dotenv()

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        api_key = _prompt_api_key()
        os.environ["GEMINI_API_KEY"] = api_key

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

    if report_md:
        with open("monthly_cfo_report.md", "w", encoding="utf-8") as f:
            f.write(report_md)

    if allocation:
        draw_portfolio_pie(json.dumps(allocation, ensure_ascii=False))

    if summary:
        print("\n--- Ozet ---")
        print(summary)
    else:
        print("\nRapor olusturuldu: monthly_cfo_report.md")


if __name__ == "__main__":
    main()
