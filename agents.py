from __future__ import annotations

from typing import Dict

from crewai import Agent

from tools import (
    fetch_liquid_bist100_stocks,
    fetch_top_tefas_funds,
    fetch_tuik_inflation,
)


def create_agents(llm_pro: object, llm_flash: object) -> Dict[str, Agent]:
    """Create and return configured CrewAI agents."""
    data_collector = Agent(
        role="Data Collector & Analyst",
        goal=(
            "Extract and clean real-time Turkish market data: "
            "TUİK inflation, top TEFAS funds, and liquid BIST 100 stocks."
        ),
        backstory=(
            "You are a meticulous market data engineer specialized in Turkey. "
            "You prioritize data quality, consistency, and clear JSON outputs."
        ),
        tools=[fetch_tuik_inflation, fetch_top_tefas_funds, fetch_liquid_bist100_stocks],
        llm=llm_flash,
        verbose=True,
        allow_delegation=False,
    )

    strategist = Agent(
        role="Financial Strategist",
        goal=(
            "Build an inflation-beating model portfolio based on risk tolerance, "
            "with clear short, medium, and long-term allocation."
        ),
        backstory=(
            "You are a disciplined portfolio strategist with experience in Turkish "
            "equities, fixed income, and commodities. You communicate with precision."
        ),
        llm=llm_pro,
        verbose=True,
        allow_delegation=False,
    )

    reporter = Agent(
        role="Reporting Specialist & CFO",
        goal=(
            "Produce a professional Turkish financial newsletter and a concise "
            "terminal summary, and visualize the allocation."
        ),
        backstory=(
            "You are a CFO-level communicator who translates strategy into "
            "clear, actionable language for Turkish investors."
        ),
        llm=llm_pro,
        verbose=True,
        allow_delegation=False,
    )

    return {
        "data_collector": data_collector,
        "strategist": strategist,
        "reporter": reporter,
    }
