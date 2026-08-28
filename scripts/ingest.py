"""Populate the database with price, news, and fundamental data for a ticker.

Must be run before any pipeline run that uses the SQL-backed tools.

    python scripts/ingest.py TICKER [YYYY-MM-DD]

If as_of_date is omitted, today is used. The script fetches the preceding
180 days of price history, recent news (up to MAX_NEWS_ITEMS), and quarterly
fundamentals, then commits everything atomically. Re-running for the same
ticker/date is safe — the ingest functions are idempotent.
"""

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.db.connection import get_connection
from src.db.ingest import ensure_company, ingest_fundamentals, ingest_news, ingest_prices


def main() -> None:
    ticker     = sys.argv[1] if len(sys.argv) > 1 else "AAPL"
    as_of_date = date.fromisoformat(sys.argv[2]) if len(sys.argv) > 2 else date.today()

    print(f"Ingesting {ticker} as of {as_of_date} ...")

    with get_connection() as conn:
        ensure_company(ticker, conn)

        n_prices = ingest_prices(ticker, as_of_date, conn)
        print(f"  price_bar:        {n_prices} rows inserted")

        n_news = ingest_news(ticker, as_of_date, conn)
        print(f"  news_item:        {n_news} rows inserted")

        n_fundamentals = ingest_fundamentals(ticker, conn)
        print(f"  fundamental_fact: {n_fundamentals} rows inserted")

    print("Done (committed).")


if __name__ == "__main__":
    main()
