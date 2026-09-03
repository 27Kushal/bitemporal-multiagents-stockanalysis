"""Database operations for tracking runs, agent messages, and verdicts."""

import json
from typing import Any
from psycopg import Connection

from src.state import RunConfig, JudgeVerdict


def insert_run(conn: Connection, config: RunConfig) -> str:
    """Insert a new run with status='running' and return its UUID."""
    sql = """
        INSERT INTO run (ticker, as_of_date, mode, analyst_model, debater_model, judge_model, debate_rounds)
        VALUES (%(ticker)s, %(as_of_date)s, %(mode)s, %(analyst_model)s, %(debater_model)s, %(judge_model)s, %(debate_rounds)s)
        RETURNING id
    """
    params = {
        "ticker": config.ticker,
        "as_of_date": config.as_of_date,
        "mode": config.mode,
        "analyst_model": config.analyst_model,
        "debater_model": config.debater_model,
        "judge_model": config.judge_model,
        "debate_rounds": config.debate_rounds,
    }
    cur = conn.execute(sql, params)
    return str(cur.fetchone()[0])


def insert_agent_messages(conn: Connection, run_id: str, llm_calls: list[dict[str, Any]]) -> None:
    """Insert all LLM call logs into the agent_message table."""
    if not llm_calls:
        return

    sql = """
        INSERT INTO agent_message (
            run_id, agent_name, model, attempt, prompt_tokens, 
            completion_tokens, latency_s, payload, success, created_at
        )
        VALUES (
            %(run_id)s, %(agent)s, %(model)s, %(attempt)s, %(prompt_tokens)s,
            %(completion_tokens)s, %(latency_s)s, %(payload)s, %(success)s, %(timestamp)s
        )
    """
    for call in llm_calls:
        params = call.copy()
        params["run_id"] = run_id
        # PostgreSQL JSONB needs string input if we use dict, psycopg3 can do it with json.dumps
        params["payload"] = json.dumps(call["payload"])
        conn.execute(sql, params)


def mark_run_completed(conn: Connection, run_id: str) -> None:
    """Mark a run as successfully completed."""
    conn.execute(
        "UPDATE run SET status = 'completed', completed_at = now() WHERE id = %s",
        (run_id,)
    )


def mark_run_failed(conn: Connection, run_id: str) -> None:
    """Mark a run as failed."""
    conn.execute(
        "UPDATE run SET status = 'failed' WHERE id = %s",
        (run_id,)
    )


def insert_verdict(conn: Connection, run_id: str, verdict: JudgeVerdict) -> None:
    """Insert the final judge's verdict."""
    sql = """
        INSERT INTO verdict (run_id, recommendation, reasoning, strongest_counterpoint, confidence)
        VALUES (%s, %s, %s, %s, %s)
    """
    conn.execute(sql, (
        run_id,
        verdict.recommendation,
        verdict.reasoning,
        verdict.strongest_counterpoint,
        verdict.confidence
    ))
