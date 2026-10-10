"""JSON-only LLM client with Ollama/Gemma integration, typed fixture fallback, and bounded retries."""
from __future__ import annotations

import json
import logging
from pathlib import Path
import time
from typing import TypeVar

from pydantic import BaseModel, ValidationError

from backend import config
from backend.llm.gemma import GemmaServiceError, clean_json_str, get_gemma_service
from backend.registry import db

log = logging.getLogger(__name__)
T = TypeVar("T", bound=BaseModel)
FIXTURES = Path(__file__).parent / "fixtures"


class LLMError(RuntimeError):
    pass


def _fixture(fn: str) -> dict:
    path = FIXTURES / f"{fn}.json"
    if not path.is_file():
        raise LLMError(f"No mock fixture is available for {fn}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise LLMError(f"Fixture {fn} is invalid: {exc}") from exc


def _run_mock(fn: str, schema: type[T]) -> T:
    data = _fixture(fn)
    db.log_llm_call(fn, "mock", 0, 0, 0, True)
    try:
        return schema.model_validate(data)
    except ValidationError as exc:
        raise LLMError(f"Mock fixture {fn} failed schema validation: {exc}") from exc


def call_json(
    fn: str,
    tier: str,
    messages: list[dict],
    schema: type[T],
    retries: int = 2,
    timeout_s: float | None = None,
    options: dict[str, Any] | None = None,
    fallback_to_mock: bool = True,
) -> T:
    """Call language model (Gemma 4B intake or 12B reason) returning validated schema object."""
    if config.MOCK_LLM:
        if not fallback_to_mock:
            raise LLMError(f"{fn} requires source-grounded extraction; mock responses are disabled")
        return _run_mock(fn, schema)

    # If configured for Ollama provider
    if config.LLM_PROVIDER == "ollama":
        gemma = get_gemma_service()
        model = gemma.model_for_tier(tier)
        try:
            parsed, usage = gemma.generate_json(
                tier=tier,
                messages=messages,
                schema=schema,
                retries=retries,
                options=options,
                timeout_s=timeout_s,
            )
            db.log_llm_call(
                fn,
                model,
                usage.get("prompt_tokens", 0),
                usage.get("completion_tokens", 0),
                usage.get("total_duration_ms", 0),
                False,
            )
            return parsed
        except Exception as exc:
            if fallback_to_mock and config.LLM_FALLBACK_TO_MOCK:
                log.warning(
                    "Ollama inference for %s (%s) failed (%s); falling back to typed mock fixture",
                    fn,
                    model,
                    exc,
                )
                return _run_mock(fn, schema)
            raise LLMError(f"{fn} Ollama inference failed: {exc}") from exc

    # Generic OpenAI / llama-server fallback provider
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise LLMError("Install the openai package to use openai/llama-server provider") from exc

    url, model = (
        (config.INTAKE_URL, config.INTAKE_MODEL)
        if tier == "intake"
        else (config.REASON_URL, config.REASON_MODEL)
    )
    client = OpenAI(base_url=url, api_key="local", timeout=config.LLM_TIMEOUT_S)
    conversation = list(messages)
    last_error = None

    for attempt in range(retries + 1):
        start = time.monotonic()
        try:
            response = client.chat.completions.create(
                model=model,
                messages=conversation,
                temperature=0,
                response_format={"type": "json_object"},
            )
            body = response.choices[0].message.content or ""
            cleaned = clean_json_str(body)
            usage = response.usage
            db.log_llm_call(
                fn,
                model,
                getattr(usage, "prompt_tokens", 0),
                getattr(usage, "completion_tokens", 0),
                int((time.monotonic() - start) * 1000),
                False,
            )
            return schema.model_validate_json(cleaned)
        except ValidationError as exc:
            last_error = exc
            if attempt < retries:
                conversation.extend([
                    {"role": "assistant", "content": body},
                    {"role": "user", "content": f"Correct the JSON to match the required schema. Validation error: {exc}"},
                ])
        except Exception as exc:
            if fallback_to_mock and config.LLM_FALLBACK_TO_MOCK:
                log.warning("OpenAI inference for %s failed (%s); falling back to mock fixture", fn, exc)
                return _run_mock(fn, schema)
            raise LLMError(f"{fn} inference failed: {exc}") from exc

    if fallback_to_mock and config.LLM_FALLBACK_TO_MOCK:
        log.warning("Inference output did not match schema after retries; falling back to mock fixture")
        return _run_mock(fn, schema)
    raise LLMError(f"{fn} output did not match schema after {retries + 1} attempts: {last_error}")
