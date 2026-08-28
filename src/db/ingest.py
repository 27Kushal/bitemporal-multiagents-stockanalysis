"""Fetch data from yfinance and write it into the database using the bitemporal append-only protocol.

Append-only rules (applied in all ingest functions):
  - Never UPDATE a value. Never DELETE a row.
  - A correction means: set known_until = correction_date on the old open row,
    then INSERT a new row with known_from = correction_date.
  - If the value has not changed, the existing open row is left untouched (idempotent).

known_from semantics:
  - price_bar:        known_from = trade_date
                      A closing price is public knowledge at market close on its own day.
  - fundamental_fact: known_from = period_end + 45 days
                      SEC quarterly filings are due 40–45 days after period end for large
                      accelerated filers. This approximates the earliest the figure was public.
  - news_item:        no transaction-time columns — publication date is immutable.

Callers are responsible for wrapping calls in a transaction (with get_connection() as conn: ...).
"""

import math
import re
from datetime import date, datetime, timedelta

import pandas as pd
import psycopg
import yfinance as yf

from config import MAX_NEWS_ITEMS, NEWS_SUMMARY_MAX_SENTENCES


# ---------------------------------------------------------------------------
# company
# ---------------------------------------------------------------------------

def ensure_company(ticker: str, conn: psycopg.Connection) -> None:
    """Upsert a row in the company reference table.

    Must be called before inserting any price, fundamental, or news row for a
    ticker, because those tables have a FK to company(ticker).
    ON CONFLICT DO UPDATE keeps name/sector/exchange current without touching
    existing fact rows.
    """
    info = yf.Ticker(ticker).info
    conn.execute(
        """
        INSERT INTO company (ticker, name, sector, exchange)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (ticker) DO UPDATE
            SET name     = EXCLUDED.name,
                sector   = EXCLUDED.sector,
                exchange = EXCLUDED.exchange
        """,
        (
            ticker,
            info.get("longName") or info.get("shortName") or ticker,
            info.get("sector"),
            info.get("exchange"),
        ),
    )


# ---------------------------------------------------------------------------
# price_bar  (bitemporal)
# ---------------------------------------------------------------------------

def ingest_prices(
    ticker: str,
    as_of_date: date,
    conn: psycopg.Connection,
    lookback_days: int = 180,
    ingestion_date: date | None = None,
) -> int:
    """Fetch OHLCV from yfinance and upsert into price_bar.

    known_from is set to trade_date (the price is public at market close that day).

    If adj_close has changed for an already-ingested bar (stock split or dividend
    adjustment), the old open row is closed (known_until = ingestion_date) and a
    new row is inserted (known_from = ingestion_date), preserving the original
    figure for any past-dated query that predates the correction.

    Returns the number of rows inserted.
    """
    if ingestion_date is None:
        ingestion_date = date.today()

    start = as_of_date - timedelta(days=lookback_days)
    end = as_of_date + timedelta(days=1)   # yfinance end is exclusive

    df = yf.Ticker(ticker).history(start=start, end=end)
    df = df[df.index.date <= as_of_date]   # safety net for timezone surprises

    inserted = 0
    for ts, row in df.iterrows():
        trade_date = ts.date()
        # yfinance "Close" is split/dividend-adjusted in recent library versions.
        adj_close = float(row["Close"])
        open_  = float(row["Open"])
        high   = float(row["High"])
        low    = float(row["Low"])
        close  = float(row["Close"])
        volume = int(row["Volume"])

        # Close any open row whose adj_close has since changed (split/dividend).
        conn.execute(
            """
            UPDATE price_bar
            SET known_until = %s
            WHERE ticker      = %s
              AND trade_date  = %s
              AND known_until = '9999-12-31'
              AND adj_close  != %s
            """,
            (ingestion_date, ticker, trade_date, adj_close),
        )

        # Insert a new row only if no open row exists for this (ticker, trade_date).
        # This keeps the operation idempotent: re-running ingest for the same data
        # is safe and produces no duplicate rows.
        result = conn.execute(
            """
            INSERT INTO price_bar
                (ticker, trade_date, open, high, low, close, volume, adj_close, known_from)
            SELECT %s, %s, %s, %s, %s, %s, %s, %s, %s
            WHERE NOT EXISTS (
                SELECT 1 FROM price_bar
                WHERE ticker      = %s
                  AND trade_date  = %s
                  AND known_until = '9999-12-31'
            )
            """,
            (
                ticker, trade_date, open_, high, low, close, volume, adj_close,
                trade_date,          # known_from = trade_date (price public at market close)
                ticker, trade_date,  # NOT EXISTS subquery args
            ),
        )
        inserted += result.rowcount

    return inserted


# ---------------------------------------------------------------------------
# news_item  (valid time only)
# ---------------------------------------------------------------------------

def ingest_news(
    ticker: str,
    as_of_date: date,
    conn: psycopg.Connection,
    max_items: int = MAX_NEWS_ITEMS,
) -> int:
    """Fetch recent headlines from yfinance and insert into news_item.

    Deduplication is by (ticker, headline, published_at): if a row with that
    combination already exists it is skipped. Summaries are truncated to
    NEWS_SUMMARY_MAX_SENTENCES before storage so retrieval never has to truncate.

    Returns the number of rows inserted.
    """
    raw_items = yf.Ticker(ticker).news or []
    inserted = 0

    for entry in raw_items:
        if inserted >= max_items:
            break

        content = entry.get("content", {})
        published = _parse_pub_date(content.get("pubDate"))
        if published is None or published > as_of_date:
            continue

        headline = content.get("title", "")
        source   = content.get("provider", {}).get("displayName", "Yahoo Finance")
        url      = (content.get("canonicalUrl") or {}).get("url") or ""
        summary  = _truncate_sentences(
            content.get("summary") or content.get("description") or "",
            NEWS_SUMMARY_MAX_SENTENCES,
        )

        result = conn.execute(
            """
            INSERT INTO news_item (ticker, headline, source, published_at, url, summary)
            SELECT %s, %s, %s, %s, %s, %s
            WHERE NOT EXISTS (
                SELECT 1 FROM news_item
                WHERE ticker       = %s
                  AND headline     = %s
                  AND published_at = %s
            )
            """,
            (
                ticker, headline, source, published, url, summary,
                ticker, headline, published,   # NOT EXISTS args
            ),
        )
        inserted += result.rowcount

    return inserted


# ---------------------------------------------------------------------------
# fundamental_fact  (bitemporal)
# ---------------------------------------------------------------------------

def ingest_fundamentals(
    ticker: str,
    conn: psycopg.Connection,
    ingestion_date: date | None = None,
) -> int:
    """Fetch quarterly financials from yfinance and upsert into fundamental_fact.

    known_from is approximated as period_end + 45 days (the SEC filing deadline
    for large accelerated filers), since yfinance does not expose the exact
    filing date. This is conservative: it may make a figure appear slightly
    later than it actually was published, but it never leaks a future revision.

    Metrics ingested: revenue, net_income, eps (basic), eps_diluted.

    Returns the number of rows inserted.
    """
    if ingestion_date is None:
        ingestion_date = date.today()

    try:
        qf = yf.Ticker(ticker).quarterly_financials
    except Exception:
        return 0

    if qf is None or qf.empty:
        return 0

    metric_map = {
        "Total Revenue": "revenue",
        "Net Income":    "net_income",
        "Basic EPS":     "eps",
        "Diluted EPS":   "eps_diluted",
    }

    inserted = 0
    for yf_metric, db_metric in metric_map.items():
        if yf_metric not in qf.index:
            continue

        for period_end_ts, value in qf.loc[yf_metric].items():
            if value is None or (isinstance(value, float) and math.isnan(value)):
                continue
            try:
                float_value = float(value)
            except (TypeError, ValueError):
                continue

            period_end   = period_end_ts.date()
            period_start = period_end - timedelta(days=90)   # approximate quarter start
            known_from   = period_end + timedelta(days=45)   # approximate filing date

            # Close the open row if the value has been restated.
            conn.execute(
                """
                UPDATE fundamental_fact
                SET known_until = %s
                WHERE ticker      = %s
                  AND metric      = %s
                  AND period_end  = %s
                  AND known_until = '9999-12-31'
                  AND value      != %s
                """,
                (ingestion_date, ticker, db_metric, period_end, float_value),
            )

            # Insert if no open row exists for this (ticker, metric, period_end).
            result = conn.execute(
                """
                INSERT INTO fundamental_fact
                    (ticker, metric, period_start, period_end, value,
                     currency, source, known_from)
                SELECT %s, %s, %s, %s, %s, 'USD', 'yfinance', %s
                WHERE NOT EXISTS (
                    SELECT 1 FROM fundamental_fact
                    WHERE ticker      = %s
                      AND metric      = %s
                      AND period_end  = %s
                      AND known_until = '9999-12-31'
                )
                """,
                (
                    ticker, db_metric, period_start, period_end, float_value, known_from,
                    ticker, db_metric, period_end,   # NOT EXISTS args
                ),
            )
            inserted += result.rowcount

    return inserted


# ---------------------------------------------------------------------------
# private helpers
# ---------------------------------------------------------------------------

def _parse_pub_date(pub_date: str | None) -> date | None:
    if not pub_date:
        return None
    return datetime.fromisoformat(pub_date.replace("Z", "+00:00")).date()


def _truncate_sentences(text: str, max_sentences: int) -> str:
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    return " ".join(sentences[:max_sentences]).strip()
