"""Compare Baseline vs Multi-Agent runs from the database.

Queries the `run`, `verdict`, and `agent_message` tables to analyze:
1. Recommendation alignment (Agreement vs Disagreement rate)
2. Confidence level shifts
3. Resource utilization (Token count, Latency, and Cost overhead)
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.db.connection import get_connection


def fetch_comparison_data():
    """Fetch paired baseline and multi_agent runs that completed for the same ticker & as_of_date."""
    sql = """
    WITH run_metrics AS (
        SELECT 
            r.id,
            r.ticker,
            r.as_of_date,
            r.mode,
            v.recommendation,
            v.confidence,
            v.reasoning,
            COALESCE(SUM(m.prompt_tokens), 0) AS total_prompt_tokens,
            COALESCE(SUM(m.completion_tokens), 0) AS total_completion_tokens,
            COALESCE(SUM(m.latency_s), 0) AS total_latency_s,
            COUNT(m.id) AS message_count
        FROM run r
        JOIN verdict v ON v.run_id = r.id
        LEFT JOIN agent_message m ON m.run_id = r.id
        WHERE r.status = 'completed'
        GROUP BY r.id, r.ticker, r.as_of_date, r.mode, v.recommendation, v.confidence, v.reasoning
    )
    SELECT 
        b.ticker,
        b.as_of_date,
        -- Baseline data
        b.recommendation AS bl_rec,
        b.confidence AS bl_conf,
        b.total_prompt_tokens + b.total_completion_tokens AS bl_tokens,
        b.total_latency_s AS bl_latency,
        -- Multi-Agent data
        m.recommendation AS ma_rec,
        m.confidence AS ma_conf,
        m.total_prompt_tokens + m.total_completion_tokens AS ma_tokens,
        m.total_latency_s AS ma_latency,
        m.message_count AS ma_messages,
        -- Comparison flags
        (b.recommendation = m.recommendation) AS agreement
    FROM run_metrics b
    JOIN run_metrics m 
      ON b.ticker = m.ticker 
     AND b.as_of_date = m.as_of_date 
     AND b.mode = 'baseline' 
     AND m.mode = 'multi_agent'
    ORDER BY b.ticker, b.as_of_date DESC;
    """
    with get_connection() as conn:
        return conn.execute(sql).fetchall()


def print_report(rows):
    print("\n" + "=" * 95)
    print("      EXPERIMENT EVALUATION: BASELINE VS MULTI-AGENT RUN COMPARISON")
    print("=" * 95)

    if not rows:
        print("\nNo paired completed runs found in the database yet.")
        print("Tip: Run eval/run_matrix.py to execute both modes across test dates.\n")
        print("=" * 95 + "\n")
        return

    # Header
    print(f"\n{'Ticker':<8} {'As-Of Date':<12} {'Baseline':<16} {'Multi-Agent':<16} {'Agreement':<12} {'Tokens (BL/MA)':<16} {'Latency'}")
    print("-" * 95)

    agree_count = 0
    total = len(rows)
    total_bl_tokens = 0
    total_ma_tokens = 0
    total_bl_lat = 0
    total_ma_lat = 0

    for r in rows:
        ticker, as_of, bl_rec, bl_conf, bl_tok, bl_lat, ma_rec, ma_conf, ma_tok, ma_lat, ma_msgs, agree = r
        
        if agree:
            agree_count += 1
            status = "MATCH"
        else:
            status = "DIVERGED"

        bl_str = f"{bl_rec.upper()} ({bl_conf})"
        ma_str = f"{ma_rec.upper()} ({ma_conf})"
        tok_str = f"{bl_tok:,} / {ma_tok:,}"
        lat_str = f"{float(bl_lat):.1f}s / {float(ma_lat):.1f}s"

        print(f"{ticker:<8} {str(as_of):<12} {bl_str:<16} {ma_str:<16} {status:<12} {tok_str:<16} {lat_str}")

        total_bl_tokens += bl_tok
        total_ma_tokens += ma_tok
        total_bl_lat += float(bl_lat)
        total_ma_lat += float(ma_lat)

    print("-" * 95)
    agree_pct = (agree_count / total) * 100
    token_mult = (total_ma_tokens / total_bl_tokens) if total_bl_tokens > 0 else 0
    lat_mult = (total_ma_lat / total_bl_lat) if total_bl_lat > 0 else 0

    print("\n--- AGGREGATE SUMMARY METRICS ---")
    print(f"• Total Paired Experiments : {total}")
    print(f"• Recommendation Agreement : {agree_count}/{total} ({agree_pct:.1f}%)")
    print(f"• Average Multi-Agent Token Overhead : {token_mult:.1f}x tokens vs Baseline")
    print(f"• Average Multi-Agent Latency Overhead: {lat_mult:.1f}x latency vs Baseline")
    print("=" * 95 + "\n")


if __name__ == "__main__":
    data = fetch_comparison_data()
    print_report(data)
