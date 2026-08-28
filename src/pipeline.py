"""Orchestration entry points. run_baseline() here; run_multi_agent() in Phase 4.

Both paths call _gather_raw_data() for their tool data — this is what makes
the "identical data in, only routing differs" invariant structural rather
than just a convention to remember.
"""

from datetime import date

from src.agents.baseline import run_baseline_agent
from src.state import RunConfig, RunState
from src.tools.indicators import get_indicators
from src.tools.news import get_news
from src.tools.prices import get_price_history, get_price_snapshot


def _gather_raw_data(ticker: str, as_of_date: date) -> dict:
    """Fetch price/indicator/news data, bounded to as_of_date."""
    price_df = get_price_history(ticker, as_of_date)
    return {
        "price_snapshot": get_price_snapshot(price_df),
        "indicators": get_indicators(price_df),
        "news": get_news(ticker, as_of_date),
    }


def run_baseline(config: RunConfig) -> RunState:
    run_state = RunState(config=config)
    data = _gather_raw_data(config.ticker, config.as_of_date)
    run_state.verdict = run_baseline_agent(
        run_state, data["price_snapshot"], data["indicators"], data["news"]
    )
    return run_state
