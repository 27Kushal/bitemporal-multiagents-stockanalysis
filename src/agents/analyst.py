"""The Analyst agent. Distils raw data into a factual report, with no bias."""

import json
from src.llm import call_llm
from src.state import RunState, AnalystReport


def run_analyst(
    run_state: RunState,
    price_snapshot: dict,
    indicators: dict,
    news: list,
) -> AnalystReport:
    """Read raw data and return a structured AnalystReport."""
    
    news_json = [{"date": str(n.published), "headline": n.headline, "summary": n.summary} for n in news]
    
    system_prompt = (
        "You are a senior financial analyst. Your job is to distil raw market data into "
        "a clean, objective summary of key facts. You must not express a bullish or bearish bias. "
        "You must not make a buy/hold/sell recommendation. Identify the most critical facts "
        "from the provided prices, technical indicators, and news."
    )
    
    user_prompt = (
        f"Price Snapshot: {json.dumps(price_snapshot)}\n"
        f"Technical Indicators: {json.dumps(indicators)}\n"
        f"News Items: {json.dumps(news_json)}\n\n"
        "Generate your AnalystReport based on this data."
    )
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
    
    return call_llm(
        model=run_state.config.analyst_model,
        messages=messages,
        response_model=AnalystReport,
        run_state=run_state,
        agent_name="analyst"
    )
