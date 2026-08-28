"""Single entry point for all model calls, via Ollama's OpenAI-compatible endpoint."""

import time
from datetime import datetime, timezone

from openai import OpenAI
from pydantic import BaseModel

from config import OLLAMA_BASE_URL, KEEP_ALIVE
from src.state import RunState

_client = OpenAI(base_url=OLLAMA_BASE_URL, api_key="ollama")  # Ollama ignores the key


def call_llm(
    model: str,
    messages: list[dict],
    response_model: type[BaseModel],
    run_state: RunState,
    agent_name: str,
    max_retries: int = 3,
) -> BaseModel:
    """Call `model` with `messages`, constrained to `response_model`'s JSON schema.

    On a malformed or non-conforming reply, feeds the error back to the model
    and retries (up to max_retries) rather than crashing the run. Every
    attempt, successful or not, is appended to run_state.llm_calls.
    """
    working_messages = list(messages)
    last_error: Exception | None = None

    for attempt in range(1, max_retries + 1):
        start = time.monotonic()
        try:
            # Ollama's OpenAI-compatible endpoint doesn't honor a per-request
            # num_ctx override (confirmed against v0.31.2) — the context window
            # is baked into the model itself; see config.DEFAULT_MODEL.
            completion = _client.beta.chat.completions.parse(
                model=model,
                messages=working_messages,
                response_format=response_model,
                extra_body={"keep_alive": KEEP_ALIVE},
            )
        except Exception as exc:  # malformed JSON, schema mismatch, connection error, etc.
            last_error = exc
            latency = time.monotonic() - start
            _log_call(run_state, agent_name, model, attempt, None, None, latency, success=False)
            working_messages = _with_correction(messages, str(exc))
            continue

        latency = time.monotonic() - start
        usage = completion.usage
        prompt_tokens = usage.prompt_tokens if usage else None
        completion_tokens = usage.completion_tokens if usage else None
        message = completion.choices[0].message

        if message.parsed is None:
            last_error = ValueError(message.refusal or "model returned no parsed content")
            _log_call(run_state, agent_name, model, attempt, prompt_tokens, completion_tokens, latency, success=False)
            working_messages = _with_correction(messages, str(last_error))
            continue

        _log_call(run_state, agent_name, model, attempt, prompt_tokens, completion_tokens, latency, success=True)
        return message.parsed

    raise RuntimeError(
        f"{agent_name}: failed to get a valid {response_model.__name__} "
        f"from {model} after {max_retries} attempts: {last_error}"
    )


def _with_correction(original_messages: list[dict], error: str) -> list[dict]:
    correction = (
        "Your previous response could not be parsed into the required JSON schema. "
        f"Error: {error}. Reply again with ONLY valid JSON matching the schema."
    )
    return original_messages + [{"role": "user", "content": correction}]


def _log_call(run_state, agent_name, model, attempt, prompt_tokens, completion_tokens, latency_s, success):
    run_state.llm_calls.append({
        "agent": agent_name,
        "model": model,
        "attempt": attempt,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "latency_s": round(latency_s, 3),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "success": success,
    })
