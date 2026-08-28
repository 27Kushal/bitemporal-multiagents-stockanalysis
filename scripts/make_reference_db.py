"""
Generate two reference files for teacher presentation:
  1. reference_database.db  — SQLite database with all 7 tables populated
  2. database_reference.html — Standalone HTML showing every table beautifully
"""

import json
import sqlite3
from pathlib import Path

OUT_DIR   = Path("/Users/kushalbagla/Documents/Kushal/llm-debate-memo/reference_db")
OUT_DIR.mkdir(exist_ok=True)
DB_PATH   = OUT_DIR / "reference_database.db"
HTML_PATH = OUT_DIR / "database_reference.html"

if DB_PATH.exists():
    DB_PATH.unlink()

# ── 1. SCHEMA ─────────────────────────────────────────────────────────────────
conn = sqlite3.connect(str(DB_PATH))
conn.execute("PRAGMA foreign_keys = ON")
conn.executescript("""
CREATE TABLE company (
    ticker TEXT PRIMARY KEY, name TEXT NOT NULL, sector TEXT, exchange TEXT
);
CREATE TABLE price_bar (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker TEXT NOT NULL REFERENCES company(ticker),
    trade_date TEXT NOT NULL, open REAL, high REAL, low REAL, close REAL,
    volume INTEGER, adj_close REAL,
    known_from TEXT NOT NULL,
    known_until TEXT NOT NULL DEFAULT '9999-12-31'
);
CREATE TABLE fundamental_fact (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker TEXT NOT NULL REFERENCES company(ticker),
    metric TEXT NOT NULL, period_start TEXT NOT NULL, period_end TEXT NOT NULL,
    value REAL, currency TEXT DEFAULT 'USD', source TEXT,
    known_from TEXT NOT NULL,
    known_until TEXT NOT NULL DEFAULT '9999-12-31'
);
CREATE TABLE news_item (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker TEXT NOT NULL REFERENCES company(ticker),
    headline TEXT NOT NULL, source TEXT, published_at TEXT NOT NULL,
    url TEXT, summary TEXT,
    ingested_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE TABLE run (
    id TEXT PRIMARY KEY,
    ticker TEXT NOT NULL REFERENCES company(ticker),
    as_of_date TEXT NOT NULL,
    mode TEXT NOT NULL CHECK (mode IN ('baseline','multi_agent')),
    analyst_model TEXT, debater_model TEXT, judge_model TEXT,
    debate_rounds INTEGER DEFAULT 1,
    started_at TEXT NOT NULL, completed_at TEXT,
    status TEXT NOT NULL DEFAULT 'running'
          CHECK (status IN ('running','completed','failed'))
);
CREATE TABLE agent_message (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL REFERENCES run(id),
    agent_name TEXT NOT NULL, model TEXT NOT NULL,
    attempt INTEGER NOT NULL DEFAULT 1,
    prompt_tokens INTEGER, completion_tokens INTEGER, latency_s REAL,
    payload TEXT NOT NULL, success INTEGER NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE TABLE verdict (
    run_id TEXT PRIMARY KEY REFERENCES run(id),
    recommendation TEXT NOT NULL CHECK (recommendation IN ('buy','hold','sell')),
    reasoning TEXT NOT NULL, strongest_counterpoint TEXT NOT NULL,
    confidence TEXT NOT NULL CHECK (confidence IN ('low','medium','high')),
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
""")

# ── 2. SEED DATA ──────────────────────────────────────────────────────────────
conn.executemany("INSERT INTO company VALUES (?,?,?,?)", [
    ("AAPL", "Apple Inc.",            "Technology", "NASDAQ"),
    ("MSFT", "Microsoft Corporation", "Technology", "NASDAQ"),
])

price_rows = [
    ("AAPL","2024-01-02",187.15,188.44,183.89,185.20,82100000,185.20,"2024-01-02","9999-12-31"),
    ("AAPL","2024-01-03",184.22,185.88,183.43,184.25,58400000,184.25,"2024-01-03","9999-12-31"),
    ("AAPL","2024-01-04",182.15,183.09,180.63,181.91,71200000,181.91,"2024-01-04","9999-12-31"),
    ("AAPL","2024-01-05",181.99,182.99,180.57,181.18,62300000,181.18,"2024-01-05","9999-12-31"),
    ("AAPL","2024-01-08",182.09,185.60,181.89,185.56,59100000,185.56,"2024-01-08","9999-12-31"),
    ("AAPL","2024-01-09",183.92,185.15,182.73,185.14,42800000,185.14,"2024-01-09","9999-12-31"),
    ("AAPL","2024-01-10",186.06,188.44,185.83,186.86,77600000,186.86,"2024-01-10","9999-12-31"),
    ("AAPL","2024-01-11",187.15,187.70,185.67,185.59,53200000,185.59,"2024-01-11","9999-12-31"),
    ("AAPL","2024-01-12",185.77,186.54,184.35,186.01,47900000,186.01,"2024-01-12","9999-12-31"),
    ("AAPL","2024-01-16",182.16,184.12,180.63,183.63,65400000,183.63,"2024-01-16","9999-12-31"),
    ("AAPL","2024-01-17",181.42,182.44,179.30,182.68,72100000,182.68,"2024-01-17","9999-12-31"),
    ("AAPL","2024-01-18",186.09,189.30,185.83,188.63,79800000,188.63,"2024-01-18","9999-12-31"),
    ("AAPL","2024-01-19",189.33,191.95,188.82,191.56,85300000,191.56,"2024-01-19","9999-12-31"),
    ("AAPL","2024-01-22",192.30,192.81,188.78,191.83,61500000,191.83,"2024-01-22","9999-12-31"),
    ("AAPL","2024-01-23",191.37,192.96,190.96,192.35,46200000,192.35,"2024-01-23","9999-12-31"),
    ("AAPL","2024-01-24",193.30,194.40,192.12,194.17,53800000,194.17,"2024-01-24","9999-12-31"),
    ("AAPL","2024-01-25",195.42,196.38,194.34,195.57,61400000,195.57,"2024-01-25","9999-12-31"),
    ("AAPL","2024-01-26",196.19,196.90,195.07,195.89,44300000,195.89,"2024-01-26","9999-12-31"),
    ("AAPL","2024-01-29",196.16,196.33,193.53,196.10,44700000,196.10,"2024-01-29","9999-12-31"),
    ("AAPL","2024-01-30",197.14,197.78,195.60,195.89,52400000,195.89,"2024-01-30","9999-12-31"),
    ("AAPL","2024-01-31",193.52,195.01,192.35,184.40,110600000,184.40,"2024-01-31","9999-12-31"),
    ("AAPL","2024-02-01",182.51,183.13,180.53,182.53,57200000,182.53,"2024-02-01","9999-12-31"),
    ("AAPL","2024-02-02",183.17,185.84,183.12,185.04,59100000,185.04,"2024-02-02","9999-12-31"),
    ("AAPL","2024-02-05",187.60,189.20,187.60,187.68,52400000,187.68,"2024-02-05","9999-12-31"),
    ("AAPL","2024-02-06",186.87,187.31,183.84,184.57,65100000,184.57,"2024-02-06","9999-12-31"),
    ("AAPL","2024-02-07",183.45,183.99,181.20,183.86,50300000,183.86,"2024-02-07","9999-12-31"),
    ("AAPL","2024-02-08",183.52,184.95,183.14,184.15,40800000,184.15,"2024-02-08","9999-12-31"),
    ("AAPL","2024-02-09",184.61,185.24,182.98,184.37,56200000,184.37,"2024-02-09","9999-12-31"),
    ("AAPL","2024-02-12",183.95,185.09,183.60,184.47,51100000,184.47,"2024-02-12","9999-12-31"),
    ("AAPL","2024-02-13",183.33,183.35,181.17,181.68,81400000,181.68,"2024-02-13","9999-12-31"),
    ("AAPL","2024-02-14",182.10,183.97,181.57,183.16,55300000,183.16,"2024-02-14","9999-12-31"),
    ("AAPL","2024-02-15",184.35,184.95,182.47,184.15,52100000,184.15,"2024-02-15","9999-12-31"),
    ("AAPL","2024-02-16",184.38,185.85,183.49,183.86,68400000,183.86,"2024-02-16","9999-12-31"),
    # dividend adjustment on 2024-03-05: original rows (closed)
    ("AAPL","2024-02-20",181.86,182.57,180.63,181.56,67300000,181.56,"2024-02-20","2024-03-05"),
    ("AAPL","2024-02-21",179.55,181.93,179.07,182.32,60100000,182.32,"2024-02-21","2024-03-05"),
    # corrected rows (adj_close reduced by $0.24 dividend)
    ("AAPL","2024-02-20",181.86,182.57,180.63,181.56,67300000,181.32,"2024-03-05","9999-12-31"),
    ("AAPL","2024-02-21",179.55,181.93,179.07,182.32,60100000,182.08,"2024-03-05","9999-12-31"),
    ("AAPL","2024-02-22",183.94,185.35,183.58,184.37,48200000,184.13,"2024-03-05","9999-12-31"),
    ("AAPL","2024-02-23",186.89,188.54,186.31,182.52,62300000,182.28,"2024-03-05","9999-12-31"),
    ("AAPL","2024-02-26",182.50,183.54,181.11,182.63,49100000,182.39,"2024-02-26","9999-12-31"),
    ("AAPL","2024-02-27",182.24,183.65,181.93,182.63,55800000,182.39,"2024-02-27","9999-12-31"),
    ("AAPL","2024-02-28",182.86,183.43,181.34,181.42,65700000,181.18,"2024-02-28","9999-12-31"),
    ("AAPL","2024-02-29",180.64,181.44,178.99,180.75,71300000,180.51,"2024-02-29","9999-12-31"),
]
conn.executemany(
    "INSERT INTO price_bar(ticker,trade_date,open,high,low,close,volume,adj_close,known_from,known_until)"
    " VALUES(?,?,?,?,?,?,?,?,?,?)", price_rows)

fund_rows = [
    ("AAPL","revenue",   "2023-10-01","2023-12-31",119575.0,"USD","yfinance","2024-02-14","9999-12-31"),
    # RESTATEMENT: original $33,916M -> corrected $33,800M on 2024-06-15
    ("AAPL","net_income","2023-10-01","2023-12-31", 33916.0,"USD","yfinance","2024-02-14","2024-06-15"),
    ("AAPL","net_income","2023-10-01","2023-12-31", 33800.0,"USD","yfinance","2024-06-15","9999-12-31"),
    ("AAPL","eps",       "2023-10-01","2023-12-31",     2.18,"USD","yfinance","2024-02-14","9999-12-31"),
    ("AAPL","revenue",   "2023-07-01","2023-09-30", 89498.0,"USD","yfinance","2023-11-13","9999-12-31"),
    ("AAPL","net_income","2023-07-01","2023-09-30", 22956.0,"USD","yfinance","2023-11-13","9999-12-31"),
    ("AAPL","eps",       "2023-07-01","2023-09-30",     1.46,"USD","yfinance","2023-11-13","9999-12-31"),
    ("MSFT","revenue",   "2023-10-01","2023-12-31", 62020.0,"USD","yfinance","2024-02-13","9999-12-31"),
    ("MSFT","net_income","2023-10-01","2023-12-31", 21870.0,"USD","yfinance","2024-02-13","9999-12-31"),
]
conn.executemany(
    "INSERT INTO fundamental_fact(ticker,metric,period_start,period_end,value,currency,source,known_from,known_until)"
    " VALUES(?,?,?,?,?,?,?,?,?)", fund_rows)

news_rows = [
    ("AAPL","Apple Reports Q1 FY2024 Revenue of $119.6B, EPS of $2.18",
     "Reuters","2024-02-01","https://reuters.com/apple-q1-2024",
     "Apple Inc. reported quarterly revenue of $119.6 billion, beating analyst estimates. CEO Tim Cook cited strong iPhone 15 demand and Services growth as key drivers."),
    ("AAPL","Apple Vision Pro Launches to Mixed Critical Reception",
     "Bloomberg","2024-02-02","https://bloomberg.com/apple-vision-pro-launch",
     "Apple's $3,499 spatial computing headset went on sale to long queues at Apple Stores. Reviewers praised the display quality but questioned the use cases at the current price."),
    ("AAPL","Apple Faces Antitrust Scrutiny Over App Store Fees in EU",
     "Financial Times","2024-01-25","https://ft.com/apple-antitrust-2024",
     "EU regulators opened a formal investigation into Apple's App Store commission structure under the Digital Markets Act. Apple could face fines of up to 10% of global annual revenue."),
    ("AAPL","iPhone Sales in China Decline for Third Consecutive Quarter",
     "Wall Street Journal","2024-02-08","https://wsj.com/apple-china-2024",
     "IDC data shows Apple's China smartphone shipments fell 13% year-over-year in Q4 2023 as Huawei regained market share following the Mate 60 Pro launch."),
    ("AAPL","Analysts Raise AAPL Price Targets After Earnings Beat",
     "CNBC","2024-02-02","https://cnbc.com/apple-price-targets-2024",
     "Morgan Stanley raised its Apple target to $220 from $195, citing accelerating Services growth and Vision Pro as a new long-term revenue stream."),
]
conn.executemany(
    "INSERT INTO news_item(ticker,headline,source,published_at,url,summary) VALUES(?,?,?,?,?,?)",
    news_rows)

MODEL = "qwen2.5-7b-ctx8k"
conn.executemany("INSERT INTO run VALUES(?,?,?,?,?,?,?,?,?,?,?)", [
    ("run-bl-20240301","AAPL","2024-03-01","baseline",
     MODEL,MODEL,MODEL,1,"2024-03-15 09:00:00","2024-03-15 09:00:38","completed"),
    ("run-ma-20240301","AAPL","2024-03-01","multi_agent",
     MODEL,MODEL,MODEL,1,"2024-03-15 10:00:00","2024-03-15 10:02:31","completed"),
    ("run-bl-failed",  "AAPL","2024-03-01","baseline",
     MODEL,MODEL,MODEL,1,"2024-03-15 08:55:00",None,"failed"),
])

bl_p = {"recommendation":"hold",
        "reasoning":"RSI at 54.3 is neutral. MACD histogram +0.42 suggests mild upward momentum. Price has stabilised at $180-185 for two weeks post-earnings. Net income $33.9B and revenue $119.6B beat consensus, but management guided cautiously on China. Vision Pro adds optionality.",
        "strongest_counterpoint":"China revenue decline of 13% YoY is accelerating. If Huawei 5G recovery continues, iPhone faces structural headwinds not yet fully priced in.",
        "confidence":"medium"}
an_p = {"price_snapshot":{"last_close":180.75,"pct_change_1d":-0.37,"pct_change_5d":-1.14,"pct_change_21d":-7.81},
        "indicators":{"rsi_14":54.3,"macd":0.61,"macd_signal":0.19,"macd_histogram":0.42},
        "key_points":["Revenue $119.6B and EPS $2.18 beat estimates","Services grew 11.3% YoY, now 22% of revenue","China iPhone shipments down 13% YoY","Vision Pro launched at $3,499","RSI neutral; price consolidating 3 weeks post-earnings"]}
bu_p = {"stance":"bull","round":1,
        "claims":["Services at 22% of revenue provides recurring high-margin base","EPS beat on high volume shows earnings quality","Technical base at $180-185 is classic consolidation","Vision Pro positions Apple for next computing platform"],
        "rebuttal_to":[]}
be_p = {"stance":"bear","round":1,
        "claims":["China decline 13% YoY is structural — Huawei Mate 60 has genuine 5G","P/E 27x prices in China recovery not yet visible","Vision Pro sold under 200k units in launch week — TAM unclear","MACD histogram shrinking — momentum fading"],
        "rebuttal_to":["Services growth real but margins under regulatory pressure (EU DMA)"]}
jd_p = {"recommendation":"buy",
        "reasoning":"After weighing both sides, the bull case is more compelling on a 6-12 month horizon. Services recurring revenue and EPS beat provide an earnings floor. China risk is real but partially priced in by the 7.8% post-earnings decline. $180-185 technical base offers a defined risk level.",
        "strongest_counterpoint":"A continued Huawei market share gain could compress iPhone revenue by $8-12B annually, requiring Services margin expansion to compensate.",
        "confidence":"high"}

conn.executemany(
    "INSERT INTO agent_message(run_id,agent_name,model,attempt,prompt_tokens,completion_tokens,latency_s,payload,success)"
    " VALUES(?,?,?,?,?,?,?,?,?)", [
    ("run-bl-20240301","baseline",MODEL,1,512,187,3.241,json.dumps(bl_p),1),
    ("run-ma-20240301","analyst", MODEL,1,498,241,4.123,json.dumps(an_p),1),
    ("run-ma-20240301","bull",    MODEL,1,621,198,3.891,json.dumps(bu_p),1),
    ("run-ma-20240301","bear",    MODEL,1,634, 42,1.204,json.dumps({"error":"unexpected token at position 312"}),0),
    ("run-ma-20240301","bear",    MODEL,2,697,211,3.512,json.dumps(be_p),1),
    ("run-ma-20240301","judge",   MODEL,1,889,274,4.891,json.dumps(jd_p),1),
])
conn.executemany(
    "INSERT INTO verdict(run_id,recommendation,reasoning,strongest_counterpoint,confidence) VALUES(?,?,?,?,?)", [
    ("run-bl-20240301","hold",bl_p["reasoning"],bl_p["strongest_counterpoint"],"medium"),
    ("run-ma-20240301","buy", jd_p["reasoning"],jd_p["strongest_counterpoint"],"high"),
])
conn.commit()
print(f"SQLite DB:  {DB_PATH}")

# ── 3. HTML ───────────────────────────────────────────────────────────────────
AS_OF = "2024-03-01"
BT    = {"known_from","known_until"}

def qrows(sql):
    cur = conn.execute(sql)
    return [d[0] for d in cur.description], cur.fetchall()

def fv(col, v):
    if v is None: return '<em style="color:#9ca3af">NULL</em>'
    c = col.lower()
    if c == "known_until" and str(v) == "9999-12-31":
        return '<b style="color:#059669">&#8734; current</b>'
    if c == "payload":
        s = str(v)
        return (f'<abbr title="{s[:500].replace(chr(34), chr(39))}">{s[:65]}&#8230;</abbr>'
                if len(s) > 65 else s)
    if c == "success":    return "&#10003;" if v == 1 else "&#10007;"
    if c == "recommendation":
        m = {"buy":"#059669","hold":"#d97706","sell":"#dc2626"}
        return f'<b style="color:{m.get(str(v),"#374151")}">{str(v).upper()}</b>'
    if c == "confidence":
        m = {"high":"#059669","medium":"#d97706","low":"#dc2626"}
        return f'<span style="color:{m.get(str(v),"#374151")};font-weight:600">{v}</span>'
    if c == "status":
        m = {"completed":"#059669","running":"#2563eb","failed":"#dc2626"}
        return f'<span style="color:{m.get(str(v),"#374151")};font-weight:600">{v}</span>'
    return str(v)

def htable(cols, data, note=""):
    hdr = "".join(
        f'<th style="background:{"#78350f" if c.lower() in BT else "#1e3a5f"};'
        f'color:#fff;padding:8px 12px;text-align:left;white-space:nowrap;'
        f'font-size:12px">{c}</th>' for c in cols)
    body = ""
    for i, row in enumerate(data):
        bg = "#f9fafb" if i % 2 == 0 else "#fff"
        tds = "".join(
            f'<td style="padding:6px 12px;border-bottom:1px solid #e5e7eb;'
            f'vertical-align:top;'
            f'{"background:#fffbeb;" if cols[j].lower() in BT else ""}'
            f'font-size:{"11px" if cols[j].lower() in {"payload","reasoning","summary","strongest_counterpoint"} else "12.5px"};'
            f'{"max-width:220px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;" if cols[j].lower() in {"payload","reasoning","summary","strongest_counterpoint"} else ""}'
            f'font-family:{"monospace" if cols[j].lower() in {"payload","id","run_id"} else "inherit"}">'
            f'{fv(cols[j], v)}</td>'
            for j, v in enumerate(row))
        body += f'<tr style="background:{bg}">{tds}</tr>'
    n = (f'<p style="font-size:12px;color:#64748b;margin:6px 0 0 2px;'
         f'line-height:1.5">{note}</p>' if note else "")
    return (f'<div style="overflow-x:auto;border-radius:8px;border:1px solid #e2e8f0">'
            f'<table style="border-collapse:collapse;width:100%">'
            f'<thead><tr>{hdr}</tr></thead>'
            f'<tbody>{body}</tbody></table></div>{n}')

def sec(title, body, icon=""):
    return (f'<section style="margin-bottom:44px">'
            f'<h2 style="font-size:17px;font-weight:700;color:#1e3a5f;'
            f'border-bottom:3px solid #1e3a5f;padding-bottom:6px;margin-bottom:14px">'
            f'{icon}&ensp;{title}</h2>{body}</section>')

def cb(code):
    return (f'<pre style="background:#0f172a;color:#e2e8f0;padding:14px 18px;'
            f'border-radius:8px;font-size:12px;line-height:1.7;overflow-x:auto;'
            f'margin:8px 0">{code}</pre>')

c_w, r_w   = qrows(f"""SELECT ticker,metric,period_end,value,currency,known_from,known_until
FROM fundamental_fact WHERE ticker='AAPL' AND metric='net_income'
AND period_end<='{AS_OF}' AND known_from<='{AS_OF}' AND known_until>'{AS_OF}'""")
c_wo, r_wo = qrows(f"""SELECT ticker,metric,period_end,value,currency,known_from,known_until
FROM fundamental_fact WHERE ticker='AAPL' AND metric='net_income' AND period_end<='{AS_OF}'""")

T = {
    "company":
        qrows("SELECT * FROM company"),
    "price_bar":
        qrows("SELECT id,ticker,trade_date,open,high,low,close,volume,adj_close,known_from,known_until"
              " FROM price_bar ORDER BY trade_date,known_from"),
    "fundamental_fact":
        qrows("SELECT * FROM fundamental_fact ORDER BY ticker,metric,period_end,known_from"),
    "news_item":
        qrows("SELECT id,ticker,headline,source,published_at,summary FROM news_item"),
    "run":
        qrows("SELECT id,ticker,as_of_date,mode,judge_model,debate_rounds,started_at,completed_at,status FROM run"),
    "agent_message":
        qrows("SELECT id,run_id,agent_name,model,attempt,prompt_tokens,completion_tokens,"
              "latency_s,payload,success FROM agent_message"),
    "verdict":
        qrows("SELECT run_id,recommendation,confidence,reasoning,strongest_counterpoint FROM verdict"),
}

notes = {
    "company": "Reference table (3NF). Company name, sector, and exchange are stored once and referenced by all fact tables via foreign key — never repeated.",
    "price_bar": "<b>&#9733; BITEMPORAL.</b> Rows for 2024-02-20 and 2024-02-21 each appear twice: the original row (known_until = 2024-03-05) and the dividend-adjusted row (known_from = 2024-03-05, adj_close reduced by $0.24). A query as-of any date before 2024-03-05 sees the original values. A query after sees the corrected ones. Neither row is deleted.",
    "fundamental_fact": "<b>&#9733; BITEMPORAL.</b> The two net_income rows for 2023-12-31 are the core demonstration: $33,916M (known 2024-02-14 to 2024-06-15) and $33,800M (known 2024-06-15 onwards). A run as-of 2024-03-01 reads $33,916M. A run without the predicate reads both — including the future revision.",
    "news_item": "Valid-time only. Publication date is immutable so no transaction-time columns are needed. The as-of filter is simply <code>published_at &lt;= as_of_date</code>.",
    "run": "One row per experiment. The 'failed' run has no verdict row because the transaction rolled back when the process died mid-run. Eval scripts filter <code>WHERE status = 'completed'</code>.",
    "agent_message": "Full audit trail of every AI call. Agent 'bear' has two rows: attempt 1 failed (malformed JSON returned), attempt 2 succeeded. <code>src/llm.py</code> fed the parse error back to the model and retried.",
    "verdict": "Structured columns (not JSONB) so eval queries can use <code>GROUP BY recommendation</code> or <code>WHERE confidence = 'high'</code> without parsing JSON. Baseline: HOLD (medium confidence). Multi-agent after debate: BUY (high confidence).",
}

demo_q_with = (
    f"SELECT ticker, metric, period_end, value, currency, known_from, known_until\n"
    f"FROM   fundamental_fact\n"
    f"WHERE  ticker      = 'AAPL'\n"
    f"  AND  metric      = 'net_income'\n"
    f"  AND  period_end &lt;= '{AS_OF}'\n"
    f"  AND  known_from  &lt;= '{AS_OF}'  -- we learned it by then\n"
    f"  AND  known_until  &gt;  '{AS_OF}'  -- not yet corrected"
)
demo_q_without = (
    f"SELECT ticker, metric, period_end, value, currency, known_from, known_until\n"
    f"FROM   fundamental_fact\n"
    f"WHERE  ticker      = 'AAPL'\n"
    f"  AND  metric      = 'net_income'\n"
    f"  AND  period_end &lt;= '{AS_OF}'\n"
    f"-- known_from / known_until predicates REMOVED\n"
    f"-- this query leaks future knowledge into a past-dated run"
)

html = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Bitemporal Database Reference</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:system-ui,-apple-system,sans-serif;background:#f1f5f9;
     color:#1e293b;padding:28px 32px;max-width:1440px;margin:0 auto}}
abbr{{cursor:help;text-decoration:underline dotted #94a3b8}}
code{{background:#f1f5f9;padding:1px 5px;border-radius:4px;font-size:12px}}
</style></head><body>

<header style="text-align:center;padding:36px 24px;margin-bottom:36px;
  background:linear-gradient(135deg,#1e3a5f 0%,#1d4ed8 100%);
  border-radius:14px;color:#fff">
  <h1 style="font-size:24px;font-weight:800;line-height:1.35;margin-bottom:10px">
    As-Of: A Bitemporal Database for Point-in-Time-Correct<br>Multi-Agent Stock Research
  </h1>
  <p style="font-size:13.5px;opacity:.85;max-width:680px;margin:0 auto">
    7 tables &middot; 2 bitemporal (&#9733;) &middot; Sample data: AAPL Jan&ndash;Feb 2024
    &middot; Live look-ahead bias demonstration &middot; SQLite: reference_database.db
  </p>
</header>

<div style="background:#fff;border:1px solid #e2e8f0;border-radius:10px;
  padding:14px 20px;margin-bottom:32px;font-size:13px;display:flex;gap:20px;
  flex-wrap:wrap;align-items:center">
  <b>Column highlight key:</b>
  <span style="background:#fffbeb;border:1px solid #fcd34d;padding:3px 10px;
    border-radius:6px;font-weight:600">known_from &amp; known_until</span>
  <span style="color:#64748b">Transaction-time columns &mdash; present only in bitemporal tables</span>
</div>

{sec("The Problem This Schema Solves &mdash; Look-Ahead Bias", f"""
<div style="display:grid;grid-template-columns:1fr 1fr;gap:16px">
  <div style="background:#fff;border-left:4px solid #dc2626;padding:18px;
    border-radius:0 8px 8px 0;font-size:13.5px;line-height:1.75">
    <b style="display:block;margin-bottom:8px;color:#dc2626">Without bitemporal design:</b>
    Apple reports Q1 FY2024 net income = <b>$33,916M</b> on 1 Feb 2024.<br>
    On 15 Jun 2024 they refile: correct figure = <b>$33,800M</b>.<br><br>
    A naive database runs:<br>
    <code>UPDATE fundamental_fact SET value = 33800 WHERE &hellip;</code><br><br>
    The $33,916M figure is <b>destroyed forever</b>.<br><br>
    A backtest pretending it is <em>1 March 2024</em> reads <b>$33,800M</b> &mdash;
    a number that did not exist on that date.<br>
    <b>No error. No warning. Silently wrong.</b>
  </div>
  <div style="background:#fff;border-left:4px solid #059669;padding:18px;
    border-radius:0 8px 8px 0;font-size:13.5px;line-height:1.75">
    <b style="display:block;margin-bottom:8px;color:#059669">With bitemporal design:</b>
    Both rows are stored. Nothing is ever updated or deleted.<br><br>
    A correction <em>closes</em> the old row:<br>
    <code>UPDATE &hellip; SET known_until = '2024-06-15'</code><br><br>
    And opens a new one:<br>
    <code>INSERT &hellip; known_from = '2024-06-15'</code><br><br>
    The as-of predicate:<br>
    <code>known_from &lt;= as_of AND known_until &gt; as_of</code><br><br>
    makes it <b>structurally impossible</b> to read the restated value
    for any date before the restatement.
  </div>
</div>""", "&#10071;")}

{sec(f"The Key Query &mdash; Demonstrated Live &nbsp; (as_of_date = {AS_OF})", f"""
<div style="display:grid;grid-template-columns:1fr 1fr;gap:20px">
  <div>
    <h3 style="color:#059669;font-size:14px;margin-bottom:8px">
      &#10003;&nbsp; WITH the bitemporal predicate
    </h3>
    {cb(demo_q_with)}
    {htable(c_w, r_w, "Returns $33,916M &mdash; the figure that actually existed on 1 March 2024. Correct.")}
  </div>
  <div>
    <h3 style="color:#dc2626;font-size:14px;margin-bottom:8px">
      &#10007;&nbsp; WITHOUT the predicate &nbsp;(look-ahead bias)
    </h3>
    {cb(demo_q_without)}
    {htable(c_wo, r_wo, "Returns BOTH rows &mdash; including $33,800M which only existed from June 2024. The system reads the future. This is look-ahead bias.")}
  </div>
</div>""", "&#128273;")}

{sec("Table 1 &mdash; company",                 htable(*T["company"],          note=notes["company"]),          "&#127970;")}
{sec("Table 2 &mdash; price_bar &#9733;",        htable(*T["price_bar"],        note=notes["price_bar"]),        "&#128200;")}
{sec("Table 3 &mdash; fundamental_fact &#9733;", htable(*T["fundamental_fact"], note=notes["fundamental_fact"]), "&#128202;")}
{sec("Table 4 &mdash; news_item",                htable(*T["news_item"],        note=notes["news_item"]),        "&#128240;")}
{sec("Table 5 &mdash; run",                      htable(*T["run"],              note=notes["run"]),              "&#127939;")}
{sec("Table 6 &mdash; agent_message",            htable(*T["agent_message"],    note=notes["agent_message"]),    "&#129302;")}
{sec("Table 7 &mdash; verdict",                  htable(*T["verdict"],          note=notes["verdict"]),          "&#9878;&#65039;")}

<footer style="text-align:center;color:#94a3b8;font-size:12px;margin-top:40px;
  padding-top:20px;border-top:1px solid #e2e8f0">
  Generated from db/schema.sql &nbsp;&middot;&nbsp; Sample data: AAPL (Apple Inc.), Jan&ndash;Feb 2024
  &nbsp;&middot;&nbsp; Open <b>reference_database.db</b> in DB Browser for SQLite to explore interactively
</footer>
</body></html>"""

HTML_PATH.write_text(html, encoding="utf-8")
print(f"HTML:       {HTML_PATH}")
print()
print("Files ready. Open database_reference.html in any browser.")
print("To explore the DB interactively: DB Browser for SQLite (free, dbrowser.org)")
