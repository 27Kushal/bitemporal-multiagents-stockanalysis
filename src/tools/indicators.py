"""Technical indicators — RSI-14 and MACD 12/26/9.

Phase 5: computation moved from pandas into SQL (src/db/indicators_sql.py).
The public interface is unchanged from pipeline.py's perspective — still
returns the same dict shape with the same keys.

The old pandas helpers are kept as compute_rsi_pandas / compute_macd_pandas
for unit-test comparison and as a fallback reference.
"""

from __future__ import annotations

from datetime import date

import pandas as pd

from src.db.indicators_sql import get_indicators_sql

RSI_PERIOD  = 14
MACD_FAST, MACD_SLOW, MACD_SIGNAL = 12, 26, 9


def get_indicators(ticker: str, as_of_date: date) -> dict:
    """RSI-14 and MACD 12/26/9 for ticker as known on as_of_date.

    Delegates to get_indicators_sql(), which embeds the bitemporal predicate
    (known_from <= as_of_date AND known_until > as_of_date) in the SQL query —
    the same time-boundary guarantee as prices.get_price_history().

    Returns dict with keys: rsi_14, macd, macd_signal, macd_histogram.
    Values are None when price history is too short to compute them.
    """
    return get_indicators_sql(ticker, as_of_date)


# ── pandas fallbacks (kept for comparison / unit tests) ──────────────────────

def compute_rsi_pandas(close: pd.Series, period: int = RSI_PERIOD) -> float | None:
    """Wilder's RSI on a pandas Close series. None if history is too short."""
    if len(close) <= period:
        return None
    delta    = close.diff()
    gain     = delta.clip(lower=0)
    loss     = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    rs       = avg_gain / avg_loss
    rsi      = 100 - (100 / (1 + rs))
    return round(float(rsi.iloc[-1]), 2)


def compute_macd_pandas(
    close:  pd.Series,
    fast:   int = MACD_FAST,
    slow:   int = MACD_SLOW,
    signal: int = MACD_SIGNAL,
) -> dict:
    """Standard MACD on a pandas Close series."""
    if len(close) <= slow:
        return {"macd": None, "macd_signal": None, "macd_histogram": None}
    ema_fast    = close.ewm(span=fast,   adjust=False).mean()
    ema_slow    = close.ewm(span=slow,   adjust=False).mean()
    macd_line   = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram   = macd_line - signal_line
    return {
        "macd":           round(float(macd_line.iloc[-1]),   2),
        "macd_signal":    round(float(signal_line.iloc[-1]), 2),
        "macd_histogram": round(float(histogram.iloc[-1]),   2),
    }
