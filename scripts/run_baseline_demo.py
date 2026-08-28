"""Run the baseline path once and print the resulting verdict + LLM call log.

    python scripts/run_baseline_demo.py [TICKER] [YYYY-MM-DD]
"""

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import ANALYST_MODEL, DEBATER_MODEL, JUDGE_MODEL
from src.pipeline import run_baseline
from src.state import RunConfig


def main():
    ticker = sys.argv[1] if len(sys.argv) > 1 else "AAPL"
    as_of_date = date.fromisoformat(sys.argv[2]) if len(sys.argv) > 2 else date.today()

    config = RunConfig(
        ticker=ticker,
        as_of_date=as_of_date,
        mode="baseline",
        analyst_model=ANALYST_MODEL,
        debater_model=DEBATER_MODEL,
        judge_model=JUDGE_MODEL,
    )

    run_state = run_baseline(config)

    print(f"--- baseline verdict: {ticker} as of {as_of_date} ---\n")
    print(run_state.verdict.model_dump_json(indent=2))

    print("\n--- llm calls ---")
    for call in run_state.llm_calls:
        print(call)


if __name__ == "__main__":
    main()
