"""The Judge agent. Reads the report and debate, makes a final verdict."""

from src.llm import call_llm
from src.state import RunState, AnalystReport, Argument, JudgeVerdict


def run_judge(
    run_state: RunState,
    report: AnalystReport,
    debate: list[Argument],
) -> JudgeVerdict:
    """Evaluate the debate and return a JudgeVerdict."""
    
    system_prompt = (
        "You are an impartial Judge in a financial debate. You will read an objective "
        "Analyst Report and a debate between a Bull and a Bear. "
        "Evaluate their arguments critically. Decide on a final recommendation (buy, hold, or sell). "
        "You must explicitly state the strongest counterpoint to your final decision to prove "
        "you have weighed both sides."
    )
    
    report_text = (
        f"Key Points: {report.key_points}\n"
        f"Prices: {report.price_snapshot}\n"
        f"Indicators: {report.indicators}\n"
        f"News: {[n.headline for n in report.news]}\n"
    )
    
    debate_lines = []
    for arg in debate:
        debate_lines.append(f"Round {arg.round} {arg.stance.upper()}: Claims: {arg.claims}. Rebuttals: {arg.rebuttal_to}")
    debate_text = "\n".join(debate_lines)
    
    user_prompt = (
        f"--- Analyst Report ---\n{report_text}\n\n"
        f"--- Debate Transcript ---\n{debate_text}\n\n"
        "Deliver your final JudgeVerdict."
    )
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
    
    return call_llm(
        model=run_state.config.judge_model,
        messages=messages,
        response_model=JudgeVerdict,
        run_state=run_state,
        agent_name="judge"
    )
