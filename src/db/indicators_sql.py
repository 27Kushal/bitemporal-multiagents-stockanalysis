"""RSI-14 and MACD 12/26/9 computed entirely in SQL.

Moving the indicator computation into the database means the bitemporal
as-of predicate lives in exactly one place — the same SQL that fetches the
prices also enforces the time boundary.

EMA note:
    True exponential moving averages require a recursive computation (each
    value depends on the previous). This module uses PostgreSQL recursive CTEs
    to implement the standard formula:
        EMA(t) = close(t) * k  +  EMA(t-1) * (1 - k)
    where k = 2 / (N + 1) for MACD and k = 1 / N for RSI (Wilder's smoothing).
    This matches pandas ewm(adjust=False), so numbers are directly comparable.

RSI seed:
    Wilder's method seeds the recursive EMA with a plain average of the first
    N gains and losses (rows 2..N+1 = N daily changes). Subsequent rows apply:
        avg_gain(t) = avg_gain(t-1) * (N-1)/N  +  gain(t) * 1/N

MACD seed:
    The EMA is seeded at row 1 with EMA = close (same convention as pandas
    ewm(adjust=False)). Settles after ~2x the period; with a 180-day lookback
    and a 26-day slow EMA there is plenty of warm-up history.
"""

from datetime import date, timedelta

from src.db.connection import get_connection
from config import DEFAULT_LOOKBACK_DAYS

RSI_PERIOD  = 14
MACD_FAST   = 12
MACD_SLOW   = 26
MACD_SIGNAL = 9

_SQL = """
WITH RECURSIVE

prices AS (
    SELECT trade_date, close,
           ROW_NUMBER() OVER (ORDER BY trade_date) AS rn
    FROM   price_bar
    WHERE  ticker      = %(ticker)s
      AND  trade_date   > %(start)s
      AND  trade_date  <= %(as_of)s
      AND  known_from  <= %(as_of)s
      AND  known_until  > %(as_of)s
),

changes AS (
    SELECT rn, trade_date, close,
           close - LAG(close) OVER (ORDER BY rn) AS chg
    FROM prices
),

rsi(rn, avg_gain, avg_loss) AS (
    SELECT %(rsi_seed_rn)s :: int,
           AVG(CASE WHEN chg > 0 THEN  chg ELSE 0 END),
           AVG(CASE WHEN chg < 0 THEN -chg ELSE 0 END)
    FROM changes
    WHERE rn BETWEEN 2 AND %(rsi_seed_rn)s

    UNION ALL

    SELECT c.rn,
           r.avg_gain * %(rsi_decay)s :: numeric
               + GREATEST( c.chg, 0) * %(rsi_k)s :: numeric,
           r.avg_loss * %(rsi_decay)s :: numeric
               + GREATEST(-c.chg, 0) * %(rsi_k)s :: numeric
    FROM rsi r
    JOIN changes c ON c.rn = r.rn + 1
),

ema(rn, ema_fast, ema_slow) AS (
    SELECT rn, close, close FROM prices WHERE rn = 1

    UNION ALL

    SELECT p.rn,
           p.close * %(k_fast)s :: numeric + e.ema_fast * %(d_fast)s :: numeric,
           p.close * %(k_slow)s :: numeric + e.ema_slow * %(d_slow)s :: numeric
    FROM ema e
    JOIN prices p ON p.rn = e.rn + 1
),

macd_line AS (
    SELECT rn, ema_fast - ema_slow AS macd FROM ema
),

signal_line(rn, macd, signal) AS (
    SELECT rn, macd, macd FROM macd_line WHERE rn = 1

    UNION ALL

    SELECT m.rn, m.macd,
           m.macd    * %(k_sig)s :: numeric
           + s.signal * %(d_sig)s :: numeric
    FROM signal_line s
    JOIN macd_line   m ON m.rn = s.rn + 1
),

counts AS (SELECT MAX(rn) AS n FROM prices)

SELECT
    CASE
        WHEN r.avg_loss = 0 THEN 100.0
        WHEN r.avg_gain = 0 THEN   0.0
        ELSE 100.0 - 100.0 / (1.0 + r.avg_gain / r.avg_loss)
    END          AS rsi_14,
    s.macd       AS macd,
    s.signal     AS macd_signal,
    s.macd - s.signal AS macd_histogram,
    c.n          AS row_count
FROM   rsi r
JOIN   signal_line s ON s.rn = r.rn
JOIN   counts      c ON r.rn = c.n
ORDER  BY r.rn DESC
LIMIT  1
"""


def get_indicators_sql(
    ticker: str,
    as_of_date: date,
    lookback_days: int = DEFAULT_LOOKBACK_DAYS,
) -> dict:
    """RSI-14 and MACD 12/26/9 for ticker as known on as_of_date.

    The bitemporal predicate (known_from <= as_of_date AND known_until > as_of_date)
    is embedded in the SQL — the same guarantee as prices.get_price_history().

    Returns None values when price history is too short (need >= 15 rows for RSI,
    >= 26 rows for MACD to have any meaningful value).
    """
    start = as_of_date - timedelta(days=lookback_days)

    rsi_k      = 1.0 / RSI_PERIOD
    rsi_decay  = 1.0 - rsi_k
    rsi_seed_rn = RSI_PERIOD + 1

    k_fast = 2.0 / (MACD_FAST   + 1)
    k_slow = 2.0 / (MACD_SLOW   + 1)
    k_sig  = 2.0 / (MACD_SIGNAL + 1)

    params = {
        "ticker":      ticker,
        "start":       start,
        "as_of":       as_of_date,
        "rsi_seed_rn": rsi_seed_rn,
        "rsi_k":       rsi_k,
        "rsi_decay":   rsi_decay,
        "k_fast":      k_fast,
        "k_slow":      k_slow,
        "k_sig":       k_sig,
        "d_fast":      1.0 - k_fast,
        "d_slow":      1.0 - k_slow,
        "d_sig":       1.0 - k_sig,
    }

    null_result = {
        "rsi_14": None, "macd": None,
        "macd_signal": None, "macd_histogram": None,
    }

    with get_connection() as conn:
        rows = conn.execute(_SQL, params).fetchall()

    if not rows:
        return null_result

    rsi_14, macd, macd_signal, macd_histogram, row_count = rows[0]

    if row_count is None or row_count < rsi_seed_rn:
        return null_result

    def r(v): return round(float(v), 4) if v is not None else None
    return {
        "rsi_14":         round(float(rsi_14), 2) if rsi_14 is not None else None,
        "macd":           r(macd),
        "macd_signal":    r(macd_signal),
        "macd_histogram": r(macd_histogram),
    }
