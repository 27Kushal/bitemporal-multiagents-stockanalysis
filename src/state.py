from pydantic import BaseModel
from typing import Literal
from datetime import date

class RunConfig(BaseModel):
    ticker: str
    as_of_date: date
    mode: Literal["multi_agent", "baseline"]
    debate_rounds: int = 1
    analyst_model: str   # Ollama tag, e.g. "qwen2.5:7b"
    debater_model: str
    judge_model: str

class NewsItem(BaseModel):
    headline: str
    source: str
    published: date
    summary: str

class AnalystReport(BaseModel):
    price_snapshot: dict     # last close, % change over a few windows
    indicators: dict         # computed RSI, MACD, etc.
    news: list[NewsItem]
    key_points: list[str]
    # NO recommendation — the analyst gathers, it does not decide.

class Argument(BaseModel):
    stance: Literal["bull", "bear"]
    round: int
    claims: list[str]
    rebuttal_to: list[str] = []

class JudgeVerdict(BaseModel):
    recommendation: Literal["buy", "hold", "sell"]
    reasoning: str
    strongest_counterpoint: str
    confidence: Literal["low", "medium", "high"]

class RunState(BaseModel):
    config: RunConfig
    analyst_report: AnalystReport | None = None
    debate: list[Argument] = []
    verdict: JudgeVerdict | None = None
    llm_calls: list[dict] = []
