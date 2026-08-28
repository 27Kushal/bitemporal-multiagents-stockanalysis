"""Historical price data — queries the bitemporal price_bar table.

The as-of-date correctness guarantee is now enforced by the SQL predicate:

    known_from  <= as_of_date   -- we had learned this price by then
    known_until >  as_of_date   -- and hadn't yet replaced it (e.g. after a split)

This replaces the Python-level filter (df[df.index.date <= as_of_date]) that
the previous yfinance-backed version applied manually after fetching live data.
"""

from datetime import date, timedelta

import pandas as pd

from src.db.connection import get_connection

# Trading-day windows for % change, and enough calendar-day lookback to cover
# them plus warm-up for indicators.py's MACD (needs ~35+ daily bars to settle).
PCT_CHANGE_WINDOWS = {"1d": 1, "5d": 5, "21d": 21}
DEFAULT_LOOKBACK_DAYS = 180


def get_price_history(
    ticker: str,
    as_of_date: date,
    lookback_days: int = DEFAULT_LOOKBACK_DAYS,
) -> pd.DataFrame:
    """Daily OHLCV for `ticker`, as known on as_of_date, over the preceding lookback_days.

    Returns a DataFrame with a DatetimeIndex and columns [Open, High, Low, Close, Volume],
    matching the shape returned by the previous yfinance-backed implementation so that
    get_price_snapshot() and indicators.get_indicators() work without changes.

    The bitemporal predicate (known_from <= as_of_date AND known_until > as_of_date)
    ensures that only prices visible on as_of_date are returned — adj_close revisions
    from stock splits that occurred after as_of_date are invisible to this query.
    """
    start = as_of_date - timedelta(days=lookback_days)

    query = """
        SELECT trade_date, open, high, low, close, volume
        FROM   price_bar
        WHERE  ticker      = %s
          AND  trade_date  > %s
          AND  trade_date <= %s
          AND  known_from <= %s
          AND  known_until > %s
        ORDER BY trade_date
    """

    with get_connection() as conn:
        rows = conn.execute(
            query, (ticker, start, as_of_date, as_of_date, as_of_date)
        ).fetchall()

    if not rows:
        return pd.DataFrame(columns=["Open", "High", "Low", "Close", "Volume"])

    df = pd.DataFrame(rows, columns=["trade_date", "Open", "High", "Low", "Close", "Volume"])
    df.index = pd.to_datetime(df["trade_date"])
    df.index.name = None
    df.drop(columns=["trade_date"], inplace=True)
    df = df.astype(float)
    return df


def get_price_snapshot(df: pd.DataFrame) -> dict:
    """Last close and % change over PCT_CHANGE_WINDOWS, as plain floats."""
    last_close = float(df["Close"].iloc[-1])
    snapshot = {"last_close": round(last_close, 2)}
    for label, n in PCT_CHANGE_WINDOWS.items():
        if len(df) <= n:
            snapshot[f"pct_change_{label}"] = None
            continue
        prior_close = float(df["Close"].iloc[-1 - n])
        pct_change = (last_close / prior_close - 1) * 100
        snapshot[f"pct_change_{label}"] = round(pct_change, 2)
    return snapshot
