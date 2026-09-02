"""Fetch one ticker/date through all three tools and check the as-of-date
bound and truncation caps actually hold. Run from the repo root:

    python scripts/verify_tools.py [TICKER] [YYYY-MM-DD]
"""

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import MAX_NEWS_ITEMS, NEWS_SUMMARY_MAX_SENTENCES
from src.tools.indicators import get_indicators
from src.tools.news import get_news
from src.tools.prices import get_price_history, get_price_snapshot


def main():
    ticker     = sys.argv[1] if len(sys.argv) > 1 else "AAPL"
    as_of_date = date.fromisoformat(sys.argv[2]) if len(sys.argv) > 2 else date.today()

    print(f"--- {ticker} as of {as_of_date} ---\n")

    df = get_price_history(ticker, as_of_date)
    print(f"price history: {len(df)} rows, {df.index[0].date()} to {df.index[-1].date()}")
    assert (df.index.date <= as_of_date).all(), "price history leaked a date past as_of_date"

    snapshot = get_price_snapshot(df)
    print("price snapshot:", snapshot)

    # Phase 5: get_indicators now takes (ticker, as_of_date) — SQL handles the
    # bitemporal predicate internally, same guarantee as get_price_history().
    indicators = get_indicators(ticker, as_of_date)
    print("indicators:", indicators)

    news = get_news(ticker, as_of_date)
    print(f"\nnews: {len(news)} items (cap is {MAX_NEWS_ITEMS})")
    assert len(news) <= MAX_NEWS_ITEMS, "news exceeded the item cap"
    for item in news:
        assert item.published <= as_of_date, "news item leaked a date past as_of_date"
        print(f"  [{item.published}] ({item.source}) {item.headline}")
        print(f"    {item.summary}")

    print("\nall as-of-date and cap checks passed")
    print("(inspect the summaries above by eye — truncation is regex sentence-splitting,")
    print(f" which can cut early on abbreviations; NEWS_SUMMARY_MAX_SENTENCES is {NEWS_SUMMARY_MAX_SENTENCES})")


if __name__ == "__main__":
    main()
