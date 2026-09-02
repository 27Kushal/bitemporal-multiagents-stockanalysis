"""Static defaults for the project. Per-run data lives in src/state.py's RunConfig."""

# Ollama's OpenAI-compatible endpoint. No API key needed; llm.py sends a dummy one.
OLLAMA_BASE_URL = "http://localhost:11434/v1"

# One model for everything by default, so only one model is ever loaded (~5 GB).
# Kept as three separate fields so the judge (or others) can be varied later.
#
# "qwen2.5-7b-ctx8k" is a local Modelfile derivative of qwen2.5:7b with num_ctx
# baked in (see modelfiles/qwen2.5-7b-ctx8k.Modelfile + README). Ollama's
# OpenAI-compatible endpoint does not honor a per-request num_ctx override, so
# this is the only reliable way to get an 8192 context window through that
# endpoint. It shares weights with qwen2.5:7b on disk (no extra ~5 GB).
DEFAULT_MODEL = "qwen2.5-7b-ctx8k"
ANALYST_MODEL = DEFAULT_MODEL
DEBATER_MODEL = DEFAULT_MODEL
JUDGE_MODEL = DEFAULT_MODEL

# Context window baked into the qwen2.5-7b-ctx8k Modelfile (see above). Kept
# here for reference/documentation, not passed per-request (Ollama's
# OpenAI-compatible endpoint ignores that override).
NUM_CTX = 8192

# Idle time before Ollama unloads the model, so it doesn't pin RAM between runs.
KEEP_ALIVE = "5m"

# Debate structure.
DEBATE_ROUNDS_DEFAULT = 1

# Tool output truncation, to keep prompts small.
MAX_NEWS_ITEMS = 8
NEWS_SUMMARY_MAX_SENTENCES = 2

# How many calendar days of price history to fetch for indicator computation.
# 365 days gives ~252 trading days — enough EMA warm-up for MACD(26) with headroom.
DEFAULT_LOOKBACK_DAYS = 365


# PostgreSQL connection string.
# Override at runtime with the DB_URL environment variable if your Postgres
# user, host, or database name differs from the local default.
import os
DB_URL = os.getenv("DB_URL", "postgresql://localhost/finresearch")
