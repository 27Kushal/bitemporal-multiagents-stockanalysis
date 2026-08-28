"""RSI and MACD, computed from a price DataFrame's Close column.

Implemented directly on pandas (no `ta`/`pandas-ta` dependency) — both are
short, standard formulas.
"""

import pandas as pd

RSI_PERIOD = 14
MACD_FAST, MACD_SLOW, MACD_SIGNAL = 12, 26, 9


def compute_rsi(close: pd.Series, period: int = RSI_PERIOD) -> float | None:
    """Wilder's RSI. None if there isn't enough history to have settled."""
    if len(close) <= period:
        return None
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return round(float(rsi.iloc[-1]), 2)


def compute_macd(close: pd.Series, fast: int = MACD_FAST, slow: int = MACD_SLOW, signal: int = MACD_SIGNAL) -> dict:
    """Standard MACD: fast EMA minus slow EMA, plus a signal EMA of that line."""
    if len(close) <= slow:
        return {"macd": None, "macd_signal": None, "macd_histogram": None}
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line
    return {
        "macd": round(float(macd_line.iloc[-1]), 2),
        "macd_signal": round(float(signal_line.iloc[-1]), 2),
        "macd_histogram": round(float(histogram.iloc[-1]), 2),
    }


def get_indicators(df: pd.DataFrame) -> dict:
    """RSI + MACD on df's Close column, as plain numbers (latest values only)."""
    close = df["Close"]
    indicators = {"rsi_14": compute_rsi(close)}
    indicators.update(compute_macd(close))
    return indicators
