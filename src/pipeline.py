"""Orchestration entry points. run_baseline() and run_multi_agent().

Both paths call _gather_raw_data() for their tool data — this is what makes
the "identical data in, only routing differs" invariant structural rather
than just a convention to remember.

Phase 7 change: run_multi_agent added. Uses same data gathering and DB persistence
as run_baseline, but routes through Analyst -> Bull/Bear loop -> Judge.
"""

from datetime import date

from src.agents.baseline import run_baseline_agent
from src.agents.analyst import run_analyst
from src.agents.debater import run_debater
from src.agents.judge import run_judge
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
    
    with get_connection() as conn:
        run_id = insert_run(conn, config)
        conn.commit()

    try:
        data = _gather_raw_data(config.ticker, config.as_of_date)
        verdict = run_baseline_agent(
            run_state, data["price_snapshot"], data["indicators"], data["news"]
        )
        run_state.verdict = verdict
        
        with get_connection() as conn:
            with conn.transaction():
                insert_verdict(conn, run_id, verdict)
                insert_agent_messages(conn, run_id, run_state.llm_calls)
                mark_run_completed(conn, run_id)
                
    except Exception:
        with get_connection() as conn:
            with conn.transaction():
                mark_run_failed(conn, run_id)
                insert_agent_messages(conn, run_id, run_state.llm_calls)
        raise

    return run_state


def run_multi_agent(config: RunConfig) -> RunState:
    run_state = RunState(config=config)
    
    with get_connection() as conn:
        run_id = insert_run(conn, config)
        conn.commit()

    try:
        data = _gather_raw_data(config.ticker, config.as_of_date)
        
        # 1. Analyst Phase
        report = run_analyst(run_state, data["price_snapshot"], data["indicators"], data["news"])
        run_state.analyst_report = report
        
        # 2. Debate Phase
        for round_num in range(1, config.debate_rounds + 1):
            bull_arg = run_debater(run_state, "bull", round_num, report, run_state.debate)
            run_state.debate.append(bull_arg)
            
            bear_arg = run_debater(run_state, "bear", round_num, report, run_state.debate)
            run_state.debate.append(bear_arg)
            
        # 3. Judge Phase
        verdict = run_judge(run_state, report, run_state.debate)
        run_state.verdict = verdict
        
        # Save success
        with get_connection() as conn:
            with conn.transaction():
                insert_verdict(conn, run_id, verdict)
                insert_agent_messages(conn, run_id, run_state.llm_calls)
                mark_run_completed(conn, run_id)
                
    except Exception:
        # Save failure
        with get_connection() as conn:
            with conn.transaction():
                mark_run_failed(conn, run_id)
                insert_agent_messages(conn, run_id, run_state.llm_calls)
        raise

    return run_state
