"""JSON-only LLM client with typed fixture fallback and bounded retries."""
from __future__ import annotations
import json, time
from pathlib import Path
from typing import TypeVar
from pydantic import BaseModel, ValidationError
from backend import config
from backend.registry import db

T=TypeVar("T",bound=BaseModel)
FIXTURES=Path(__file__).parent/"fixtures"
class LLMError(RuntimeError): pass

def _fixture(fn: str) -> dict:
    path=FIXTURES/f"{fn}.json"
    if not path.is_file(): raise LLMError(f"No mock fixture is available for {fn}")
    try: return json.loads(path.read_text(encoding="utf-8"))
    except (OSError,json.JSONDecodeError) as exc: raise LLMError(f"Fixture {fn} is invalid: {exc}") from exc

def call_json(fn: str, tier: str, messages: list[dict], schema: type[T], retries: int=2) -> T:
    if config.MOCK_LLM:
        data=_fixture(fn); db.log_llm_call(fn,"mock",0,0,0,True)
        try: return schema.model_validate(data)
        except ValidationError as exc: raise LLMError(f"Mock fixture {fn} failed schema validation") from exc
    try:
        from openai import OpenAI
    except ImportError as exc: raise LLMError("Install the openai package to use llama-server") from exc
    url,model=(config.INTAKE_URL,config.INTAKE_MODEL) if tier=="intake" else (config.REASON_URL,config.REASON_MODEL)
    client=OpenAI(base_url=url,api_key="local",timeout=config.LLM_TIMEOUT_S)
    conversation=list(messages); last=None
    for attempt in range(retries+1):
        start=time.monotonic()
        try:
            response=client.chat.completions.create(model=model,messages=conversation,temperature=0,response_format={"type":"json_object"})
            body=response.choices[0].message.content or ""; usage=response.usage
            db.log_llm_call(fn,model,getattr(usage,"prompt_tokens",0),getattr(usage,"completion_tokens",0),int((time.monotonic()-start)*1000),False)
            return schema.model_validate_json(body)
        except ValidationError as exc:
            last=exc
            if attempt<retries: conversation += [{"role":"assistant","content":body},{"role":"user","content":f"Correct the JSON to match the required schema. Validation error: {exc}"}]
        except Exception as exc:
            raise LLMError(f"{fn} inference failed: {exc}") from exc
    raise LLMError(f"{fn} output did not match the required schema after {retries+1} attempts: {last}")
