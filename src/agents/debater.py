"""The Debater agents (Bull and Bear)."""

from src.llm import call_llm
from src.state import RunState, AnalystReport, Argument


def run_debater(
    run_state: RunState,
    stance: str,
    round_num: int,
    report: AnalystReport,
    previous_arguments: list[Argument],
) -> Argument:
    """Read the analyst report and previous arguments, return a new Argument."""
    
    if stance == "bull":
        role_desc = "You are a 'Bull' debater. You must interpret the facts optimistically, highlighting growth, momentum, and positive catalysts. Argue for a BUY."
    elif stance == "bear":
        role_desc = "You are a 'Bear' debater. You must interpret the facts pessimistically, highlighting risks, overvaluation, and negative catalysts. Argue for a SELL."
    else:
        raise ValueError(f"Unknown stance: {stance}")

    system_prompt = (
        f"{role_desc}\n\n"
        "You will be provided with an objective Analyst Report and the debate history so far. "
        "Formulate your claims. If there are previous arguments from your opponent, directly "
        "rebut their strongest points in the 'rebuttal_to' field."
    )
    
    report_text = (
        f"Key Points: {report.key_points}\n"
        f"Prices: {report.price_snapshot}\n"
        f"Indicators: {report.indicators}\n"
        f"News: {[n.headline for n in report.news]}\n"
    )
    
    history_text = "None"
    if previous_arguments:
        history_lines = []
        for arg in previous_arguments:
            history_lines.append(f"Round {arg.round} {arg.stance.upper()}: Claims: {arg.claims}. Rebuttals: {arg.rebuttal_to}")
        history_text = "\n".join(history_lines)
    
    user_prompt = (
        f"--- Analyst Report ---\n{report_text}\n\n"
        f"--- Debate History ---\n{history_text}\n\n"
        f"Generate your Round {round_num} argument."
    )
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
    
    # We force the stance and round into the schema output via context,
    # but the LLM will construct the Pydantic Argument object.
    return call_llm(
        model=run_state.config.debater_model,
        messages=messages,
        response_model=Argument,
        run_state=run_state,
        agent_name=stance
    )
