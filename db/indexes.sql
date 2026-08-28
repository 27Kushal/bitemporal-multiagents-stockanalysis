-- =============================================================================
-- As-Of: Bitemporal Financial Research Database
-- Indexes — apply after schema.sql.
--
-- Each index is justified with: what query it serves, what column order matters.
-- Run EXPLAIN ANALYZE on the as-of query before and after applying these; the
-- scan type flip (Seq Scan → Index Scan) and timing drop are the report deliverable.
-- =============================================================================


-- -----------------------------------------------------------------------------
-- price_bar
--
-- The as-of query always starts with a ticker equality filter, then ranges on
-- trade_date, known_from, known_until. Column order: equality first (best
-- selectivity, enables index seek), then the range predicates in filter order.
-- -----------------------------------------------------------------------------
CREATE INDEX idx_price_bar_asof
    ON price_bar (ticker, trade_date, known_from, known_until);


-- -----------------------------------------------------------------------------
-- fundamental_fact
--
-- The as-of query filters on ticker + metric (both equality), then period_end
-- (the quarter must have ended by as_of_date), then known_from / known_until.
-- ticker + metric together are highly selective, so they go first.
-- -----------------------------------------------------------------------------
CREATE INDEX idx_fundamental_asof
    ON fundamental_fact (ticker, metric, period_end, known_from, known_until);


-- -----------------------------------------------------------------------------
-- news_item
--
-- Simple lookup: ticker equality + published_at range (published_at <= as_of_date).
-- No transaction-time columns — news publication dates are immutable.
-- -----------------------------------------------------------------------------
CREATE INDEX idx_news_ticker_date
    ON news_item (ticker, published_at);


-- -----------------------------------------------------------------------------
-- agent_message
--
-- Eval queries join agent_message to run on run_id, then filter by agent_name
-- (e.g. to pull only 'judge' outputs). run_id first for the join, agent_name
-- second for the filter.
-- -----------------------------------------------------------------------------
CREATE INDEX idx_agent_message_run
    ON agent_message (run_id, agent_name);


-- -----------------------------------------------------------------------------
-- run
--
-- Eval queries filter runs by ticker + as_of_date to pair baseline vs
-- multi_agent runs for the same experiment. status filter (= 'completed')
-- is low-cardinality so it is left out of the composite index; Postgres will
-- apply it as a filter after the index scan.
-- -----------------------------------------------------------------------------
CREATE INDEX idx_run_ticker_date
    ON run (ticker, as_of_date);
