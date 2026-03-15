from __future__ import annotations

from typing import Dict, List

from crewai import Task


def create_tasks(
    agents: Dict[str, object],
    risk_tolerance: str,
    investment_capital: float,
    report_type: str,
    output_type: str,
    region: str,
) -> List[Task]:
    """Create and return the ordered task list for a sequential Crew."""
    data_task = Task(
        description=(
            "Collect and clean current Turkish market data. "
            "Use tools to fetch TUİK CPI/PPI inflation, top-performing TEFAS funds, "
            "and highly liquid BIST 100 stocks. "
            "Return a single JSON object with: "
            "timestamp, inflation (CPI/PPI), tefas_top_funds, bist100_liquid. "
            "Output ONLY JSON, no extra text."
        ),
        expected_output=(
            "JSON string with keys: timestamp, inflation, tefas_top_funds, "
            "bist100_liquid. Use arrays of objects where applicable."
        ),
        agent=agents["data_collector"],
    )

    strategy_task = Task(
        description=(
            "Using the data from the previous task, design an inflation-beating "
            "model portfolio for the given risk tolerance and capital.\n"
            f"Risk Tolerance: {risk_tolerance}\n"
            f"Investment Capital (TL): {investment_capital}\n\n"
            "You must split the strategy strictly into three horizons:\n"
            "Short-Term (0-6 months), Medium-Term (6-24 months), Long-Term (2+ years).\n"
            "Provide allocation weights for Equities, Fixed Income, and Commodities "
            "per horizon. Output must be JSON ONLY. Do not wrap with code fences. "
            "No analysis, no extra text."
        ),
        expected_output=(
            "JSON with keys: short_term, medium_term, long_term. "
            "Each contains allocations for Equities, Fixed Income, Commodities "
            "as numeric percentages and brief rationale fields."
        ),
        agent=agents["strategist"],
        context=[data_task],
    )

    report_task = Task(
        description=(
            "Create a professional Turkish financial newsletter based on the "
            "strategy. The output must be entirely in Turkish and clearly separated "
            "by the three horizons (kisa/orta/uzun vade). "
            "Include a concise Turkish terminal summary. "
            "If data is missing or tools failed, clearly state this in Turkish "
            "inside the report and set data_health to 'partial'. Otherwise "
            "set data_health to 'ok'. "
            f"Report type: {report_type}. Output type: {output_type}. Region: {region}. "
            "Do NOT add any signature, closing lines, or names. "
            "If output type is bulletin, include a detailed weekly/monthly analysis "
            "with macro and micro context. "
            "If output type is advice, include short/medium/long term strategy AND "
            "specific instruments (TEFAS fund codes/names, BIST tickers, and emtia). "
            "Return a single JSON object with: report_markdown, terminal_summary, "
            "portfolio_allocation, data_health. "
            "portfolio_allocation must be a flat object with numeric weights only "
            "(no nested horizons), e.g. "
            '{"Hisse Senetleri": 48, "Sabit Getirili Menkul Kıymetler": 38, "Emtia": 14}.'
        ),
        expected_output=(
            "JSON with keys: report_markdown (Markdown string), "
            "terminal_summary (string), portfolio_allocation (object), "
            "data_health (ok|partial). "
            "All text must be Turkish. Output ONLY JSON, no extra text."
        ),
        agent=agents["reporter"],
        context=[strategy_task],
    )

    return [data_task, strategy_task, report_task]
