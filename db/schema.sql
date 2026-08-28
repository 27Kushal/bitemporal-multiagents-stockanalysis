-- =============================================================================
-- As-Of: Bitemporal Financial Research Database
-- Schema DDL — apply once against an empty PostgreSQL database.
--
-- Temporal conventions used throughout:
--   valid time       — when was this fact true in the real world?
--                      columns: trade_date (price_bar), period_start/period_end (fundamental_fact)
--   transaction time — when did the database learn / stop believing it?
--                      columns: known_from, known_until  (sentinel: 9999-12-31 = "still current")
--
-- The as-of query predicate (shared by every bitemporal table):
--   known_from  <= :as_of_date   -- we had learned it by then
--   known_until >  :as_of_date   -- and hadn't yet corrected it
--
-- Append-only discipline: never UPDATE or DELETE a value row.
-- A correction means: set known_until = correction_date on the old row,
-- then INSERT a new row with known_from = correction_date.
-- =============================================================================

-- gen_random_uuid() is built into PostgreSQL 13+. No extension needed.


-- -----------------------------------------------------------------------------
-- 1. company
--    Reference table. 3NF: one row per ticker so name/sector/exchange are
--    never repeated across thousands of price or fundamental rows.
-- -----------------------------------------------------------------------------
CREATE TABLE company (
    ticker    TEXT PRIMARY KEY,
    name      TEXT NOT NULL,
    sector    TEXT,
    exchange  TEXT
);


-- -----------------------------------------------------------------------------
-- 2. price_bar  —  BITEMPORAL
--
--    Valid time:       trade_date  — which calendar day did this bar describe?
--    Transaction time: known_from, known_until
--                      Adjusted close changes silently every time a stock split
--                      or dividend is processed. Without transaction time, the
--                      original close is destroyed; with it, old runs can still
--                      see the adj_close that existed on their as_of_date.
-- -----------------------------------------------------------------------------
CREATE TABLE price_bar (
    id          BIGSERIAL    PRIMARY KEY,
    ticker      TEXT         NOT NULL REFERENCES company(ticker),
    trade_date  DATE         NOT NULL,
    open        NUMERIC(18,4),
    high        NUMERIC(18,4),
    low         NUMERIC(18,4),
    close       NUMERIC(18,4),
    volume      BIGINT,
    adj_close   NUMERIC(18,4),
    known_from  DATE         NOT NULL,
    known_until DATE         NOT NULL DEFAULT '9999-12-31'
);


-- -----------------------------------------------------------------------------
-- 3. fundamental_fact  —  BITEMPORAL
--
--    Valid time:       period_start, period_end — which reporting period?
--    Transaction time: known_from, known_until
--                      Companies revise earnings (restatements, corrections).
--                      Two rows can share the same (ticker, metric, period_*)
--                      with non-overlapping transaction windows — that is the
--                      whole point. The naive schema stores one row and UPDATEs
--                      it; the original value is then unrecoverable.
--
--    Example:
--      (AAPL, net_income, 2023-10-01, 2023-12-31, 100, 2024-02-05, 2024-06-20)
--      (AAPL, net_income, 2023-10-01, 2023-12-31,  80, 2024-06-20, 9999-12-31)
--    An as-of query for 2024-03-01 returns 100. Correctly.
-- -----------------------------------------------------------------------------
CREATE TABLE fundamental_fact (
    id           BIGSERIAL    PRIMARY KEY,
    ticker       TEXT         NOT NULL REFERENCES company(ticker),
    metric       TEXT         NOT NULL,   -- e.g. 'net_income', 'revenue', 'eps', 'total_debt'
    period_start DATE         NOT NULL,
    period_end   DATE         NOT NULL,
    value        NUMERIC(28,4),
    currency     TEXT         DEFAULT 'USD',
    source       TEXT,                    -- 'yfinance', 'manual', etc.
    known_from   DATE         NOT NULL,
    known_until  DATE         NOT NULL DEFAULT '9999-12-31'
);


-- -----------------------------------------------------------------------------
-- 4. news_item
--    Valid time only: publication date is immutable — a headline published on
--    5 Feb 2024 was published on 5 Feb 2024, forever. No transaction-time
--    columns needed. The as-of filter is simply: published_at <= as_of_date.
-- -----------------------------------------------------------------------------
CREATE TABLE news_item (
    id           BIGSERIAL    PRIMARY KEY,
    ticker       TEXT         NOT NULL REFERENCES company(ticker),
    headline     TEXT         NOT NULL,
    source       TEXT,
    published_at DATE         NOT NULL,
    url          TEXT,
    summary      TEXT,
    ingested_at  TIMESTAMPTZ  NOT NULL DEFAULT now()
);


-- -----------------------------------------------------------------------------
-- 5. run
--    One row per experiment. Status starts as 'running' and is flipped to
--    'completed' inside the same transaction that writes the verdict row.
--    If the process dies mid-run the transaction rolls back and this row
--    disappears — there are no partial corpses to silently corrupt eval averages.
-- -----------------------------------------------------------------------------
CREATE TABLE run (
    id            UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    ticker        TEXT         NOT NULL REFERENCES company(ticker),
    as_of_date    DATE         NOT NULL,
    mode          TEXT         NOT NULL CHECK (mode IN ('baseline', 'multi_agent')),
    analyst_model TEXT,
    debater_model TEXT,
    judge_model   TEXT,
    debate_rounds INT          DEFAULT 1,
    started_at    TIMESTAMPTZ  NOT NULL DEFAULT now(),
    completed_at  TIMESTAMPTZ,
    status        TEXT         NOT NULL DEFAULT 'running'
                               CHECK (status IN ('running', 'completed', 'failed'))
);


-- -----------------------------------------------------------------------------
-- 6. agent_message
--    Every LLM call — successful or not — appended here. Replaces the
--    in-memory run_state.llm_calls list that currently vanishes at process exit.
--    payload is JSONB: the full structured Pydantic output (or the partial
--    response on failed attempts).
--    ON DELETE CASCADE: dropping a run drops all its messages cleanly.
-- -----------------------------------------------------------------------------
CREATE TABLE agent_message (
    id                BIGSERIAL    PRIMARY KEY,
    run_id            UUID         NOT NULL REFERENCES run(id) ON DELETE CASCADE,
    agent_name        TEXT         NOT NULL,  -- 'baseline', 'analyst', 'bull', 'bear', 'judge'
    model             TEXT         NOT NULL,
    attempt           INT          NOT NULL DEFAULT 1,
    prompt_tokens     INT,
    completion_tokens INT,
    latency_s         NUMERIC(8,3),
    payload           JSONB        NOT NULL,  -- structured output; {} on failure
    success           BOOLEAN      NOT NULL,
    created_at        TIMESTAMPTZ  NOT NULL DEFAULT now()
);


-- -----------------------------------------------------------------------------
-- 7. verdict
--    The judge's final output, one per run. Structured separately from
--    agent_message so eval queries don't have to parse JSONB to compare
--    recommendations across runs.
--    Primary key is run_id — one verdict per run, enforced by the schema.
-- -----------------------------------------------------------------------------
CREATE TABLE verdict (
    run_id                 UUID   PRIMARY KEY REFERENCES run(id) ON DELETE CASCADE,
    recommendation         TEXT   NOT NULL CHECK (recommendation IN ('buy', 'hold', 'sell')),
    reasoning              TEXT   NOT NULL,
    strongest_counterpoint TEXT   NOT NULL,
    confidence             TEXT   NOT NULL CHECK (confidence IN ('low', 'medium', 'high')),
    created_at             TIMESTAMPTZ NOT NULL DEFAULT now()
);
