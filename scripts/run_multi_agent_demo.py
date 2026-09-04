import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import ANALYST_MODEL, DEBATER_MODEL, JUDGE_MODEL, DEBATE_ROUNDS_DEFAULT
from src.state import RunConfig
from src.pipeline import run_multi_agent


def main():
    ticker = sys.argv[1] if len(sys.argv) > 1 else "AAPL"
    as_of_date = date.fromisoformat(sys.argv[2]) if len(sys.argv) > 2 else date.today()

    print(f"--- MULTI-AGENT RUN: {ticker} as of {as_of_date} ---")
    
    config = RunConfig(
        ticker=ticker,
        as_of_date=as_of_date,
        mode="multi_agent",
        debate_rounds=DEBATE_ROUNDS_DEFAULT,
        analyst_model=ANALYST_MODEL,
        debater_model=DEBATER_MODEL,
        judge_model=JUDGE_MODEL,
    )
    
    print("\nStarting multi-agent pipeline... (this takes longer than baseline)")
    state = run_multi_agent(config)
    
    print("\n=== ANALYST REPORT ===")
    print("Key Points:")
    for pt in state.analyst_report.key_points:
        print(f" - {pt}")
        
    print("\n=== DEBATE ===")
    for arg in state.debate:
        print(f"\nRound {arg.round} | {arg.stance.upper()}")
        print("Claims:")
        for claim in arg.claims:
            print(f" - {claim}")
        if arg.rebuttal_to:
            print("Rebuttals:")
            for reb in arg.rebuttal_to:
                print(f" - {reb}")

    print("\n=== FINAL VERDICT ===")
    print(f"RECOMMENDATION: {state.verdict.recommendation.upper()} (Confidence: {state.verdict.confidence})")
    print(f"\nReasoning:\n{state.verdict.reasoning}")
    print(f"\nStrongest Counterpoint:\n{state.verdict.strongest_counterpoint}")
    
    print(f"\n[Done] Run complete. Total AI calls: {len(state.llm_calls)}")


if __name__ == "__main__":
    main()
