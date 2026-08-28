"""Baseline path: one model, one call, given all the raw data at once.

No separate gathering/distillation step and no debate — this is the point of
comparison against the multi-agent path, which sees identical raw data but
routes it through an analyst, a bull/bear debate, and a judge.
"""

from src.state import JudgeVerdict, NewsItem, RunState
from src.llm import call_llm

SYSTEM_PROMPT = (
    "You are an equity research assistant. You will be given price data, "
    "technical indicators, and recent news for a stock as of a specific date. "
    "Produce a single recommendation (buy, hold, or sell) grounded only in the "
    "data provided. Give clear reasoning, state the strongest counterpoint "
    "against your own recommendation, and give a confidence level."
)


def run_baseline_agent(
    run_state: RunState,
    price_snapshot: dict,
    indicators: dict,
    news: list[NewsItem],
) -> JudgeVerdict:
    prompt = _build_prompt(run_state.config.ticker, run_state.config.as_of_date, price_snapshot, indicators, news)
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": prompt},
    ]
    return call_llm(
        model=run_state.config.judge_model,
        messages=messages,
        response_model=JudgeVerdict,
        run_state=run_state,
        agent_name="baseline",
    )


def _build_prompt(ticker: str, as_of_date, price_snapshot: dict, indicators: dict, news: list[NewsItem]) -> str:
    lines = [
        f"Ticker: {ticker}",
        f"As of date: {as_of_date}",
        "",
        "Price snapshot:",
        *[f"  {key}: {value}" for key, value in price_snapshot.items()],
        "",
        "Technical indicators:",
        *[f"  {key}: {value}" for key, value in indicators.items()],
        "",
        "Recent news:",
        *_format_news(news),
        "",
        "Based only on the data above, decide buy, hold, or sell.",
    ]
    return "\n".join(lines)


def _format_news(news: list[NewsItem]) -> list[str]:
    if not news:
        return ["  (no recent news available)"]
    return [f"  [{item.published}] ({item.source}) {item.headline} — {item.summary}" for item in news]
