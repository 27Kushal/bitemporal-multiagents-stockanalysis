"""Orchestration entry points. run_baseline() here; run_multi_agent() in Phase 7.

Both paths call _gather_raw_data() for their tool data — this is what makes
the "identical data in, only routing differs" invariant structural rather
than just a convention to remember.

Phase 6 change: Database transaction wrapping. 
- Creates a 'running' record immediately and commits it.
- Gathers data and calls agents.
- On success, saves verdict + agent_messages and marks run 'completed' in one transaction.
- On crash, marks run 'failed' and saves any agent_messages up to the crash.
"""

from datetime import date

from src.agents.baseline import run_baseline_agent
from src.state import RunConfig, RunState
from src.tools.indicators import get_indicators
from src.tools.news import get_news
from src.tools.prices import get_price_history, get_price_snapshot
from src.db.connection import get_connection
from src.db.runs import insert_run, insert_agent_messages, insert_verdict, mark_run_completed, mark_run_failed


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
    
    # 1. Create run record immediately (status='running')
    with get_connection() as conn:
        run_id = insert_run(conn, config)
        conn.commit()  # commit so it exists in DB if we crash

    try:
        # 2. Gather data and run agent
        data = _gather_raw_data(config.ticker, config.as_of_date)
        verdict = run_baseline_agent(
            run_state, data["price_snapshot"], data["indicators"], data["news"]
        )
        run_state.verdict = verdict
        
        # 3. Save success state
        with get_connection() as conn:
            with conn.transaction():
                insert_verdict(conn, run_id, verdict)
                insert_agent_messages(conn, run_id, run_state.llm_calls)
                mark_run_completed(conn, run_id)
                
    except Exception:
        # 4. Save failed state and messages
        with get_connection() as conn:
            with conn.transaction():
                mark_run_failed(conn, run_id)
                insert_agent_messages(conn, run_id, run_state.llm_calls)
        raise

    return run_state
