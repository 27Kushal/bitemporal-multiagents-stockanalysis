"""Run evaluation matrix across tickers and dates.

Executes both baseline and multi_agent modes for each target scenario,
ensuring all runs are transaction-persisted in the database.
"""

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import (
    ANALYST_MODEL,
    DEBATER_MODEL,
    JUDGE_MODEL,
    DEBATE_ROUNDS_DEFAULT,
)
from src.state import RunConfig
from src.pipeline import run_baseline, run_multi_agent
from src.db.connection import get_connection
from src.db.ingest import ingest_prices, ingest_news, ingest_fundamentals, ensure_company
from eval.compare_runs import fetch_comparison_data, print_report


# Default matrix: AAPL at 2 distinct dates
DEFAULT_SCENARIOS = [
    ("AAPL", date(2024, 1, 15)),
    ("AAPL", date(2024, 3, 1)),
]


def ensure_data(ticker: str, as_of: date):
    """Ingest data for the ticker and as-of date if not already present."""
    with get_connection() as conn:
        ensure_company(ticker, conn)
        # Check if we have price bars for this date
        cnt = conn.execute(
            "SELECT count(*) FROM price_bar WHERE ticker = %s AND trade_date <= %s",
            (ticker, as_of)
        ).fetchone()[0]
        
        if cnt < 10:
            print(f"  [Ingest] Ingesting historical data for {ticker} as of {as_of}...")
            ingest_prices(ticker, as_of, conn)
            ingest_news(ticker, as_of, conn)
            ingest_fundamentals(ticker, conn)
            conn.commit()


def execute_matrix(scenarios=DEFAULT_SCENARIOS):
    print("=" * 80)
    print("              STARTING EVALUATION MATRIX RUNS")
    print("=" * 80)
    print(f"Scenarios to evaluate: {len(scenarios)}")

    for idx, (ticker, as_of) in enumerate(scenarios, 1):
        print(f"\n[{idx}/{len(scenarios)}] Processing {ticker} as of {as_of.isoformat()}...")
        ensure_data(ticker, as_of)

        cfg_bl = RunConfig(
            ticker=ticker,
            as_of_date=as_of,
            mode="baseline",
            debate_rounds=DEBATE_ROUNDS_DEFAULT,
            analyst_model=ANALYST_MODEL,
            debater_model=DEBATER_MODEL,
            judge_model=JUDGE_MODEL,
        )

        cfg_ma = RunConfig(
            ticker=ticker,
            as_of_date=as_of,
            mode="multi_agent",
            debate_rounds=DEBATE_ROUNDS_DEFAULT,
            analyst_model=ANALYST_MODEL,
            debater_model=DEBATER_MODEL,
            judge_model=JUDGE_MODEL,
        )

        print("  -> Running Baseline agent...")
        try:
            st_bl = run_baseline(cfg_bl)
            print(f"     Verdict: {st_bl.verdict.recommendation.upper()} ({st_bl.verdict.confidence})")
        except Exception as e:
            print(f"     Failed: {e}")

        print("  -> Running Multi-Agent debate...")
        try:
            st_ma = run_multi_agent(cfg_ma)
            print(f"     Verdict: {st_ma.verdict.recommendation.upper()} ({st_ma.verdict.confidence})")
        except Exception as e:
            print(f"     Failed: {e}")

    print("\nAll matrix scenarios executed.")
    # Print the comparison table
    data = fetch_comparison_data()
    print_report(data)


if __name__ == "__main__":
    execute_matrix()
