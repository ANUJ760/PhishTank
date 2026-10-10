"""Ollama integration and Gemma service for 4B (intake) and 12B (reasoning) models."""
from __future__ import annotations

import base64
import json
import logging
import re
import time
from typing import Any, TypeVar
import urllib.error
import urllib.request

from pydantic import BaseModel, ValidationError

from backend import config

log = logging.getLogger(__name__)
T = TypeVar("T", bound=BaseModel)


class GemmaServiceError(RuntimeError):
    """Base error for Gemma / Ollama service interactions."""
    pass


def clean_json_str(text: str) -> str:
    """Strip markdown fences, leading/trailing notes, and whitespace to extract pure JSON."""
    text = text.strip()
    # Match markdown json fence ```json ... ``` or ``` ... ```
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text, re.IGNORECASE)
    if match:
        text = match.group(1).strip()
    return text


class GemmaService:
    """Production-grade Ollama client managing Gemma 4B intake and 12B reasoning tiers."""

    def __init__(
        self,
        base_url: str | None = None,
        intake_model: str | None = None,
        reason_model: str | None = None,
        timeout_s: float | None = None,
    ):
        self.base_url = (base_url or config.OLLAMA_BASE_URL).rstrip("/")
        self.intake_model = intake_model or config.INTAKE_MODEL
        self.reason_model = reason_model or config.REASON_MODEL
        self.timeout_s = timeout_s or config.LLM_TIMEOUT_S

    def model_for_tier(self, tier: str) -> str:
        """Resolve the model name for the requested tier."""
        tier_lower = tier.lower()
        if tier_lower in {"intake", "4b", "intake_model"}:
            return self.intake_model
        if tier_lower in {"reason", "reasoning", "12b", "reason_model"}:
            return self.reason_model
        return tier

    def check_health(self) -> dict[str, Any]:
        """Query Ollama API to verify daemon connectivity and model availability."""
        url = f"{self.base_url}/api/tags"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "GeCompose-GemmaService"})
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            installed_models = [m.get("name", "") for m in data.get("models", [])]

            # Model tags may include ':latest' or specific tag
            intake_ready = any(
                m == self.intake_model or m.startswith(f"{self.intake_model}:") or self.intake_model.startswith(m)
                for m in installed_models
            )
            reason_ready = any(
                m == self.reason_model or m.startswith(f"{self.reason_model}:") or self.reason_model.startswith(m)
                for m in installed_models
            )

            return {
                "ok": True,
                "connected": True,
                "base_url": self.base_url,
                "installed_models": installed_models,
                "intake_model": self.intake_model,
                "intake_ready": intake_ready,
                "reason_model": self.reason_model,
                "reason_ready": reason_ready,
            }
        except urllib.error.URLError as exc:
            return {
                "ok": False,
                "connected": False,
                "base_url": self.base_url,
                "error": f"Cannot reach Ollama at {self.base_url}: {exc}",
                "intake_ready": False,
                "reason_ready": False,
                "installed_models": [],
            }
        except Exception as exc:
            return {
                "ok": False,
                "connected": False,
                "base_url": self.base_url,
                "error": str(exc),
                "intake_ready": False,
                "reason_ready": False,
                "installed_models": [],
            }

    def _convert_openai_messages_to_ollama(self, messages: list[dict]) -> list[dict]:
        """Convert standard OpenAI-style messages (including multimodal) to Ollama format."""
        ollama_messages = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content")

            if isinstance(content, str):
                ollama_messages.append({"role": role, "content": content})
            elif isinstance(content, list):
                # Multimodal content array
                text_parts = []
                images = []
                for part in content:
                    if not isinstance(part, dict):
                        continue
                    part_type = part.get("type")
                    if part_type == "text":
                        text_parts.append(part.get("text", ""))
                    elif part_type == "image_url":
                        img_url = part.get("image_url", {}).get("url", "")
                        if "base64," in img_url:
                            images.append(img_url.split("base64,")[1])
                        else:
                            images.append(img_url)
                    elif part_type == "input_audio":
                        # If audio data is embedded
                        audio_info = part.get("input_audio", {})
                        text_parts.append(f"[Audio data provided: {audio_info.get('format', 'audio')}]")

                entry: dict[str, Any] = {"role": role, "content": " ".join(text_parts)}
                if images:
                    entry["images"] = images
                ollama_messages.append(entry)
            else:
                ollama_messages.append({"role": role, "content": str(content or "")})
        return ollama_messages

    def chat_complete(
        self,
        model: str,
        messages: list[dict],
        format_json: bool = True,
        temperature: float = 0.0,
        options: dict[str, Any] | None = None,
        timeout_s: float | None = None,
    ) -> tuple[str, dict[str, Any]]:
        """Execute chat completion via Ollama native API."""
        url = f"{self.base_url}/api/chat"
        ollama_messages = self._convert_openai_messages_to_ollama(messages)

        merged_options = {"temperature": temperature}
        think_flag = False
        if options:
            merged_options.update(options)
            if "think" in merged_options:
                think_flag = bool(merged_options.pop("think"))
            elif not format_json:
                think_flag = True

        payload: dict[str, Any] = {
            "model": model,
            "messages": ollama_messages,
            "stream": False,
            "options": merged_options,
        }
        if format_json:
            payload["format"] = "json"
            payload["think"] = think_flag
        elif "think" in (options or {}):
            payload["think"] = think_flag

        data_bytes = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data_bytes,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "GeCompose-GemmaService",
            },
        )

        effective_timeout = timeout_s if timeout_s is not None else self.timeout_s
        start = time.monotonic()
        try:
            with urllib.request.urlopen(req, timeout=effective_timeout) as resp:
                result = json.loads(resp.read().decode("utf-8"))
        except urllib.error.URLError as exc:
            raise GemmaServiceError(
                f"Failed to communicate with Ollama service at {url}: {exc}. "
                f"Ensure 'ollama serve' is running and model '{model}' is pulled."
            ) from exc
        except Exception as exc:
            raise GemmaServiceError(f"Ollama chat error: {exc}") from exc

        elapsed_ms = int((time.monotonic() - start) * 1000)
        message_obj = result.get("message", {})
        content = message_obj.get("content", "")
        if not content and message_obj.get("thinking"):
            thinking_str = message_obj.get("thinking", "")
            extracted = clean_json_str(thinking_str)
            if extracted.startswith("{") or extracted.startswith("["):
                content = extracted

        usage = {
            "prompt_tokens": result.get("prompt_eval_count", 0),
            "completion_tokens": result.get("eval_count", 0),
            "total_duration_ms": elapsed_ms,
            "model": model,
        }
        return content, usage

    def generate_json(
        self,
        tier: str,
        messages: list[dict],
        schema: type[T],
        retries: int = 2,
        options: dict[str, Any] | None = None,
        timeout_s: float | None = None,
    ) -> tuple[T, dict[str, Any]]:
        """Call Gemma 4B or 12B model with schema validation and retry loop."""
        model = self.model_for_tier(tier)
        conversation = list(messages)
        last_error = None

        for attempt in range(retries + 1):
            raw_text, usage = self.chat_complete(
                model=model,
                messages=conversation,
                format_json=True,
                temperature=0.0,
                options=options,
                timeout_s=timeout_s,
            )
            cleaned = clean_json_str(raw_text)
            try:
                parsed_model = schema.model_validate_json(cleaned)
                return parsed_model, usage
            except ValidationError as exc:
                last_error = exc
                log.warning(
                    "Gemma %s output failed schema validation on attempt %d/%d: %s",
                    model,
                    attempt + 1,
                    retries + 1,
                    exc,
                )
                if attempt < retries:
                    conversation.extend([
                        {"role": "assistant", "content": raw_text},
                        {
                            "role": "user",
                            "content": (
                                f"Your response did not strictly match the required JSON schema. "
                                f"Validation error: {exc}. Please return valid JSON strictly matching the schema."
                            ),
                        },
                    ])

        raise GemmaServiceError(
            f"{model} output failed schema validation after {retries + 1} attempts: {last_error}"
        )


# Global default Gemma service instance
_default_service: GemmaService | None = None


def get_gemma_service() -> GemmaService:
    global _default_service
    if _default_service is None:
        _default_service = GemmaService()
    return _default_service
