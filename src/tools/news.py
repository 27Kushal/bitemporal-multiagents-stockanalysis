"""News headlines — queries the news_item table.

The as-of-date correctness guarantee is enforced by the SQL predicate:

    published_at <= as_of_date

News items are not bitemporal (a publication date is immutable), so there are
no known_from / known_until columns to filter. The guarantee is simply that
ingest_news() never writes a row with published_at > the ingestion's as_of_date,
and this query can never surface one.

Summaries are truncated to NEWS_SUMMARY_MAX_SENTENCES at ingest time, so no
truncation is needed here.
"""

from datetime import date

from src.db.connection import get_connection
from src.state import NewsItem
from config import MAX_NEWS_ITEMS


def get_news(
    ticker: str,
    as_of_date: date,
    max_items: int = MAX_NEWS_ITEMS,
) -> list[NewsItem]:
    """Recent headlines for `ticker` published on or before as_of_date.

    Results are ordered newest-first and capped at max_items, matching the
    behaviour of the previous yfinance-backed implementation.
    """
    query = """
        SELECT headline, source, published_at, summary
        FROM   news_item
        WHERE  ticker       = %s
          AND  published_at <= %s
        ORDER BY published_at DESC
        LIMIT %s
    """

    with get_connection() as conn:
        rows = conn.execute(query, (ticker, as_of_date, max_items)).fetchall()

    return [
        NewsItem(
            headline=row[0],
            source=row[1] or "Unknown",
            published=row[2],     # psycopg3 returns DATE as datetime.date — matches NewsItem.published
            summary=row[3] or "",
        )
        for row in rows
    ]
