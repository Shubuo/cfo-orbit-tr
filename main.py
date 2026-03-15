from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.request
from datetime import datetime
from pathlib import Path
from getpass import getpass
from typing import Any, Dict, Optional, Tuple, TypedDict

from dotenv import load_dotenv

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


def _find_conda_sqlite_lib_dir() -> str | None:
    conda_root = Path(sys.executable).resolve().parents[1]
    pkgs_dir = conda_root / "pkgs"
    if not pkgs_dir.exists():
        return None
    candidates = sorted(pkgs_dir.glob("libsqlite-*/lib/libsqlite3.0.dylib"))
    if not candidates:
        return None
    return str(candidates[-1].parent)


def _ensure_sqlite_runtime() -> None:
    # On macOS with conda, sqlite may resolve to the system dylib and fail.
    # If so, re-exec with DYLD_LIBRARY_PATH pointing to conda's libsqlite.
    if sys.platform != "darwin":
        return
    if os.environ.get("CREWAI_DYLD_PATCHED") == "1":
        return
    lib_dir = _find_conda_sqlite_lib_dir()
    if not lib_dir:
        return
    os.environ["DYLD_LIBRARY_PATH"] = lib_dir
    os.environ["CREWAI_DYLD_PATCHED"] = "1"
    os.execv(sys.executable, [sys.executable] + sys.argv)


def _ensure_crewai_storage() -> None:
    # CrewAI uses appdirs on macOS and writes under ~/Library/Application Support.
    # In restricted environments, that path can be non-writable. If so, redirect
    # HOME to a local writable directory inside the project.
    app_name = os.environ.get("CREWAI_STORAGE_DIR", Path.cwd().name)
    default_dir = Path.home() / "Library" / "Application Support" / app_name
    try:
        default_dir.mkdir(parents=True, exist_ok=True)
    except PermissionError:
        local_home = Path.cwd() / ".crewai_home"
        local_home.mkdir(parents=True, exist_ok=True)
        os.environ["HOME"] = str(local_home)


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


def _prompt_report_type() -> str:
    while True:
        value = input("Rapor Tipi (Weekly/Monthly): ").strip().lower()
        if value in ("weekly", "monthly"):
            return value
        print("Gecersiz giris. Weekly/Monthly girin.")


def _prompt_output_type() -> str:
    while True:
        value = input("Cikti Turu (Bulletin/Advice): ").strip().lower()
        if value in ("bulletin", "advice"):
            return value
        print("Gecersiz giris. Bulletin/Advice girin.")


def _prompt_region() -> str:
    while True:
        value = input("Bolge (TR): ").strip().lower()
        if value in ("tr", "turkiye", "türkiye"):
            return "TR"
        print("Gecersiz giris. TR secin.")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Personal CFO CLI")
    parser.add_argument(
        "--non-interactive",
        action="store_true",
        help="Non-interactive mode (requires env vars).",
    )
    parser.add_argument(
        "--list-models",
        action="store_true",
        help="List available Gemini models for the provided API key.",
    )
    parser.add_argument("--report-type", type=str, default="")
    parser.add_argument("--output-type", type=str, default="")
    parser.add_argument("--region", type=str, default="")
    parser.add_argument("--sandbox", action="store_true")
    parser.add_argument("--risk", type=str, default="")
    parser.add_argument("--capital", type=str, default="")
    return parser.parse_args()


def _extract_json(text: str) -> Optional[Dict[str, Any]]:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"```(?:json)?", "", text).strip()
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


def _strip_signature(text: str) -> str:
    lines = text.splitlines()
    for i, line in enumerate(lines):
        normalized = line.strip().lower()
        if normalized.startswith(
            (
                "saygılarımızla",
                "saygilarimizla",
                "saygılarımla",
                "saygilarimla",
                "saygılarla",
                "saygilarla",
            )
        ):
            return "\n".join(lines[:i]).rstrip()
    return text


def _list_gemini_models(api_key: str) -> None:
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models"
        f"?key={api_key}"
    )
    with urllib.request.urlopen(url, timeout=30) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    models = [m.get("name") for m in data.get("models", []) if "name" in m]
    print("Kullanilabilir modeller:")
    for name in models:
        print(f"- {name}")


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


def _overall_allocation(allocation: Dict[str, Any]) -> Dict[str, float]:
    # If allocation is already flat numeric, return as-is.
    if all(isinstance(v, (int, float)) for v in allocation.values()):
        return {str(k): float(v) for k, v in allocation.items()}
    # If allocation is horizon-based, compute average weights.
    try:
        st = allocation.get("short_term", {})
        mt = allocation.get("medium_term", {})
        lt = allocation.get("long_term", {})
        keys = ["equities", "fixed_income", "commodities"]
        if all(k in st for k in keys) and all(k in mt for k in keys) and all(k in lt for k in keys):
            avg = {
                "Hisse Senetleri": (float(st["equities"]) + float(mt["equities"]) + float(lt["equities"])) / 3.0,
                "Sabit Getirili Menkul Kıymetler": (
                    float(st["fixed_income"]) + float(mt["fixed_income"]) + float(lt["fixed_income"])
                )
                / 3.0,
                "Emtia": (float(st["commodities"]) + float(mt["commodities"]) + float(lt["commodities"])) / 3.0,
            }
            return avg
    except Exception:
        pass
    return {}


def _probe_llm_or_fallback(
    llm: "GoogleGenaiLLM", fallback_llm: "GoogleGenaiLLM"
) -> "GoogleGenaiLLM":
    try:
        llm.call("ping")
        return llm
    except Exception as exc:
        msg = str(exc)
        if "RESOURCE_EXHAUSTED" in msg or "Quota exceeded" in msg or "429" in msg:
            return fallback_llm
        return llm


def main() -> None:
    _ensure_sqlite_runtime()
    args = _parse_args()
    load_dotenv()

    os.environ.setdefault("CREWAI_DISABLE_TELEMETRY", "true")
    os.environ.setdefault("CREWAI_TESTING", "true")
    if args.sandbox:
        os.environ["SANDBOX_MODE"] = "true"

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        if args.non_interactive:
            print("GEMINI_API_KEY bulunamadi. Non-interactive modda .env gerekli.")
            return
        api_key = _prompt_api_key()
        os.environ["GEMINI_API_KEY"] = api_key

    if args.list_models:
        _list_gemini_models(api_key)
        return

    if args.non_interactive:
        risk_tolerance = (args.risk or os.getenv("RISK_TOLERANCE", "")).strip()
        capital_raw = (args.capital or os.getenv("INVESTMENT_CAPITAL", "")).strip()
        report_type = (args.report_type or os.getenv("REPORT_TYPE", "")).strip().lower()
        output_type = (args.output_type or os.getenv("OUTPUT_TYPE", "")).strip().lower()
        region = (args.region or os.getenv("REGION", "TR")).strip().upper()
        if not risk_tolerance or not capital_raw:
            print("Non-interactive mod icin RISK_TOLERANCE ve INVESTMENT_CAPITAL gerekli.")
            return
        if report_type not in ("weekly", "monthly"):
            print("REPORT_TYPE weekly veya monthly olmali.")
            return
        if output_type not in ("bulletin", "advice"):
            print("OUTPUT_TYPE bulletin veya advice olmali.")
            return
        try:
            investment_capital = float(capital_raw)
        except Exception:
            print("INVESTMENT_CAPITAL sayi olmali.")
            return
    else:
        risk_tolerance = _prompt_risk_tolerance()
        investment_capital = _prompt_capital()
        report_type = _prompt_report_type()
        output_type = _prompt_output_type()
        region = _prompt_region()

    _ensure_crewai_storage()

    from crewai import Crew, Process  # lazy import after storage setup
    from agents import create_agents
    from llm import GoogleGenaiLLM
    from tasks import create_tasks
    from tools import draw_portfolio_pie, fetch_liquid_bist100_stocks, fetch_top_tefas_funds, fetch_tuik_inflation
    from domain.models import MarketState, ReportInputs
    from application.reporting import (
        build_macro_micro_summary,
        build_instrument_list,
        build_missing_notice,
    )

    flash_model = os.getenv("GEMINI_FLASH_MODEL", "gemini-2.5-flash")
    pro_model = os.getenv("GEMINI_PRO_MODEL", "gemini-2.5-pro")
    flash_fallbacks = os.getenv(
        "GEMINI_FLASH_FALLBACK",
        "gemini-2.0-flash,gemini-flash-latest",
    ).split(",")
    pro_fallbacks = os.getenv(
        "GEMINI_PRO_FALLBACK",
        "gemini-pro-latest,gemini-2.0-flash",
    ).split(",")

    llm_flash = GoogleGenaiLLM(
        model=flash_model,
        temperature=0.2,
        api_key=api_key,
        fallback_models=flash_fallbacks,
    )
    llm_pro = GoogleGenaiLLM(
        model=pro_model,
        temperature=0.2,
        api_key=api_key,
        fallback_models=pro_fallbacks,
    )

    if os.getenv("GEMINI_FORCE_FLASH_FOR_PRO", "false").lower() == "true":
        llm_pro = llm_flash
    else:
        llm_pro = _probe_llm_or_fallback(llm_pro, llm_flash)

    agents = create_agents(llm_pro=llm_pro, llm_flash=llm_flash)
    tasks = create_tasks(
        agents=agents,
        risk_tolerance=risk_tolerance,
        investment_capital=investment_capital,
        report_type=report_type,
        output_type=output_type,
        region=region,
    )

    crew = Crew(
        agents=list(agents.values()),
        tasks=tasks,
        process=Process.sequential,
        verbose=True,
    )

    raw_inflation = json.loads(fetch_tuik_inflation.run())
    raw_funds = json.loads(fetch_top_tefas_funds.run())
    raw_stocks = json.loads(fetch_liquid_bist100_stocks.run())
    market_state = MarketState(
        timestamp=raw_inflation.get("timestamp", ""),
        inflation=raw_inflation.get("inflation", raw_inflation),
        tefas_top_funds=raw_funds.get("top_funds", raw_funds.get("tefas_top_funds", [])),
        bist100_liquid=raw_stocks.get("liquid_stocks", raw_stocks.get("bist100_liquid", [])),
    )

    missing_info = []
    if not market_state.inflation:
        missing_info.append("Enflasyon (TÜİK) verisi alınamadı.")
    if not market_state.tefas_top_funds:
        missing_info.append("TEFAS fon verisi alınamadı.")
    if not market_state.bist100_liquid:
        missing_info.append("BIST100 likidite verisi alınamadı.")

    inputs = ReportInputs(
        report_type=report_type,
        output_type=output_type,
        region=region,
        risk_tolerance=risk_tolerance,
        investment_capital=investment_capital,
        sandbox=os.getenv("SANDBOX_MODE", "false").lower() == "true",
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

    report_dir = Path("reports") / datetime.now().strftime("%Y-%m-%d")
    report_dir.mkdir(parents=True, exist_ok=True)
    (report_dir / "inputs.json").write_text(json.dumps(inputs.__dict__, ensure_ascii=False, indent=2), encoding="utf-8")
    (report_dir / "raw_data.json").write_text(
        json.dumps(
            {
                "inflation": market_state.inflation,
                "tefas_top_funds": market_state.tefas_top_funds,
                "bist100_liquid": market_state.bist100_liquid,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    if report_md:
        report_md = _strip_signature(report_md)
        if output_type == "bulletin":
            report_md = f"{report_md}\n\n{build_macro_micro_summary(market_state)}"
        if output_type == "advice":
            report_md = f"{report_md}\n\n{build_instrument_list(market_state)}"
        missing_block = build_missing_notice(missing_info)
        if missing_block:
            report_md = f"{report_md}\n\n{missing_block}"

        report_slug = f"{report_type}_{output_type}"
        report_file = f"report_{report_slug}.md"
        with open(report_file, "w", encoding="utf-8") as f:
            f.write(report_md)
        (report_dir / report_file).write_text(report_md, encoding="utf-8")
        (report_dir / "output.json").write_text(
            json.dumps(
                {"report_markdown": report_md, "terminal_summary": summary, "portfolio_allocation": allocation},
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

    if allocation:
        overall = _overall_allocation(allocation)
        normalized = _normalize_allocation(overall)
        if _validate_allocation(normalized):
            draw_portfolio_pie.run(json.dumps(normalized, ensure_ascii=False))

    if summary:
        print("\n--- Ozet ---")
        print(summary)
        (report_dir / f"summary_{report_type}_{output_type}.txt").write_text(summary, encoding="utf-8")
        if missing_info:
            print("\n--- Eksik Veriler ---")
            for item in missing_info:
                print(f"- {item}")
    else:
        print(f"\nRapor olusturuldu: {report_file}")


if __name__ == "__main__":
    main()
