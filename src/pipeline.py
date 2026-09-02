"""Orchestration entry points. run_baseline() here; run_multi_agent() in Phase 7.

Both paths call _gather_raw_data() for their tool data — this is what makes
the "identical data in, only routing differs" invariant structural rather
than just a convention to remember.

Phase 5 change: get_indicators now takes (ticker, as_of_date) instead of a
DataFrame. It fetches its own price data from the DB with the same bitemporal
predicate as get_price_history(). get_price_history() is still called here
because get_price_snapshot() still needs the DataFrame.
"""

from datetime import date

from src.agents.baseline import run_baseline_agent
from src.state import RunConfig, RunState
from src.tools.indicators import get_indicators
from src.tools.news import get_news
from src.tools.prices import get_price_history, get_price_snapshot


def _gather_raw_data(ticker: str, as_of_date: date) -> dict:
    """Fetch price/indicator/news data, all bounded to as_of_date."""
    price_df = get_price_history(ticker, as_of_date)
    return {
        "price_snapshot": get_price_snapshot(price_df),
        "indicators":     get_indicators(ticker, as_of_date),
        "news":           get_news(ticker, as_of_date),
    }


def run_baseline(config: RunConfig) -> RunState:
    run_state = RunState(config=config)
    data = _gather_raw_data(config.ticker, config.as_of_date)
    run_state.verdict = run_baseline_agent(
        run_state, data["price_snapshot"], data["indicators"], data["news"]
    )
    return run_state
