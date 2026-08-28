# As-Of: A Bitemporal Database for Point-in-Time-Correct Multi-Agent Stock Research

A DBMS course project that solves look-ahead bias in financial backtesting using a
**bitemporal PostgreSQL schema**, then runs both a single-model baseline and a
structured multi-agent debate against the same point-in-time-correct data.

Inspired by TradingAgents (Xiao et al., 2024, [arXiv:2412.20138](https://arxiv.org/abs/2412.20138)),
but the central contribution is the database design, not the agents.

---

## The Problem

Companies revise their financials. A naive database `UPDATE`s the row in place —
the original figure is destroyed. A backtest pretending it is "1 March 2024" then
reads the June 2024 correction silently. No error. No warning. The system is
reading the future.

The bitemporal schema stores **both rows**, keyed by when each value was the
current truth (`known_from`, `known_until`). The as-of query predicate:

```sql
known_from <= as_of_date AND known_until > as_of_date
```

makes it structurally impossible to read a future revision for a past-dated run.
The correctness guarantee moves from application convention to database invariant.

---

## Two Comparison Paths

Both paths call the same `_gather_raw_data()` function — identical data in,
only the routing differs:

| Path | What happens |
|---|---|
| **Baseline** | One model, one prompt with all data, one call → `JudgeVerdict` |
| **Multi-agent** | Analyst distils data (no recommendation) → Bull ↔ Bear debate → Judge → `JudgeVerdict` |

Everything runs locally via [Ollama](https://ollama.com) — no API keys, no paid services.

---

## Setup

### 1. Python environment

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Ollama model

```bash
ollama pull qwen2.5:7b
ollama create qwen2.5-7b-ctx8k -f modelfiles/qwen2.5-7b-ctx8k.Modelfile
```

`qwen2.5-7b-ctx8k` is a local Modelfile derivative of `qwen2.5:7b` with an
8192-token context window baked in. Ollama's OpenAI-compatible endpoint (used here)
ignores per-request `num_ctx` — the Modelfile is the reliable fix. It shares weights
on disk with `qwen2.5:7b`, so costs a few KB extra, not another 5 GB.

### 3. PostgreSQL

```bash
# macOS with Homebrew
brew install postgresql@16
brew services start postgresql@16
createdb finresearch
psql -d finresearch -f db/schema.sql
psql -d finresearch -f db/indexes.sql
```

Override the default connection string if needed:

```bash
export DB_URL="postgresql://user:password@host/finresearch"
```

---

## Usage

### Ingest data (run once per ticker/date)

```bash
python scripts/ingest.py AAPL 2024-03-01
```

Fetches prices, news, and fundamentals from yfinance and writes them into
the bitemporal tables using the append-only protocol. All four inserts share
one transaction — either everything commits or nothing does.

### Run baseline

```bash
python scripts/run_baseline_demo.py AAPL 2024-03-01
```

### Verify as-of-date correctness

```bash
python scripts/verify_tools.py AAPL 2024-03-01
```

Asserts that every price row and every news item is on or before `as_of_date`.
The assertion is now enforced by SQL predicates, not Python filters.

### Generate reference database (for demos)

```bash
python scripts/make_reference_db.py
# → reference_db/reference_database.db  (SQLite, open in DB Browser for SQLite)
# → reference_db/database_reference.html (open in any browser)
```

---

## Project Structure

```
.
├── config.py                  # All constants (model names, DB_URL, caps)
├── db/
│   ├── schema.sql             # 7-table DDL: company, price_bar★, fundamental_fact★,
│   │                          #   news_item, run, agent_message, verdict
│   └── indexes.sql            # 5 composite indexes (equality cols first for B-tree)
├── src/
│   ├── state.py               # Pydantic models: RunConfig, AnalystReport, JudgeVerdict …
│   ├── llm.py                 # Single call_llm() gateway, retry loop, call logging
│   ├── pipeline.py            # _gather_raw_data() shared by both paths
│   ├── db/
│   │   ├── connection.py      # get_connection() factory
│   │   └── ingest.py          # ensure_company, ingest_prices/news/fundamentals
│   ├── tools/
│   │   ├── prices.py          # get_price_history() — bitemporal SQL query
│   │   ├── news.py            # get_news() — published_at SQL filter
│   │   └── indicators.py      # RSI-14, MACD 12/26/9 (pandas, moves to SQL in Phase 5)
│   └── agents/
│       └── baseline.py        # Single-model path → JudgeVerdict
├── scripts/
│   ├── ingest.py              # CLI: python scripts/ingest.py TICKER [DATE]
│   ├── run_baseline_demo.py   # CLI: run baseline path and print verdict
│   ├── verify_tools.py        # Assert as-of-date bounds hold end-to-end
│   └── make_reference_db.py   # Generate SQLite + HTML reference for demos
├── eval/                      # Phase 8: comparison queries (not yet implemented)
├── modelfiles/
│   └── qwen2.5-7b-ctx8k.Modelfile
└── requirements.txt
```

★ Bitemporal tables — have `known_from` and `known_until` columns.

---

## Implementation Phases

| Phase | Status | What |
|---|---|---|
| 1 — Config + state models | ✅ Done | `config.py`, `src/state.py`, Modelfile |
| 2 — Baseline agent | ✅ Done | `src/llm.py`, `src/agents/baseline.py`, `src/pipeline.py`, tools |
| 3 — Bitemporal schema | ✅ Done | `db/schema.sql`, `db/indexes.sql` |
| 4 — Ingest + SQL tools | ✅ Done | `src/db/`, `scripts/ingest.py`, tools rewritten to SQL |
| 5 — SQL indicators | 🔲 Next | RSI/MACD in SQL window functions |
| 6 — DB-persisted runs | 🔲 | Transaction-wrapped pipeline, `run`/`agent_message`/`verdict` written |
| 7 — Multi-agent path | 🔲 | Analyst → Bull ↔ Bear → Judge |
| 8 — Demo + eval | 🔲 | Look-ahead bias live demo, `eval/compare_runs.py` |

---

## Design Notes

- **Append-only protocol**: ingest functions never `UPDATE` a value or `DELETE` a row.
  A correction closes the old row (`known_until = correction_date`) and opens a new one.
- **`known_from` semantics**: `trade_date` for prices (public at market close);
  `period_end + 45 days` for fundamentals (SEC filing deadline approximation).
- **Single LLM gateway**: all AI calls go through `src/llm.py:call_llm()`.
  Retry loop feeds parse errors back to the model (up to 3 attempts).
- **Shared data path**: `_gather_raw_data()` is called by both baseline and
  multi-agent — structurally guarantees identical data, not just a convention.
- **One model, all roles**: `qwen2.5-7b-ctx8k` is the default for every agent.
  Only one model is loaded in memory at a time — ~5 GB total footprint.

When done with the project:
```bash
ollama rm qwen2.5-7b-ctx8k qwen2.5:7b
```
