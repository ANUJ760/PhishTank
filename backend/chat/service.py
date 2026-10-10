"""Official Google GenAI SDK integration for Gemma 4 via Gemini API."""
from __future__ import annotations

import logging
from typing import AsyncGenerator, Generator, List, Optional
from google import genai
from google.genai import types
from google.genai.errors import APIError

from backend import config

log = logging.getLogger(__name__)


class GeminiAPIException(Exception):
    """Custom exception wrapper for Gemini API operations."""
    def __init__(self, message: str, status_code: int = 500, detail: Optional[str] = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.detail = detail or message


class GemmaChatService:
    """Production service communicating with Gemma 4 through Google Gemini API."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
        system_prompt: Optional[str] = None,
    ):
        self.api_key = api_key or config.GEMINI_API_KEY
        self.model_name = model_name or config.MODEL_NAME
        self.system_prompt = system_prompt or config.SYSTEM_PROMPT
        self._client: Optional[genai.Client] = None

    def _get_client(self) -> genai.Client:
        if not self.api_key:
            raise GeminiAPIException(
                message="GEMINI_API_KEY is not configured.",
                status_code=500,
                detail="Please provide a valid Google Gemini API key via GEMINI_API_KEY environment variable."
            )
        if self._client is None:
            self._client = genai.Client(api_key=self.api_key)
        return self._client

    def _convert_messages(self, messages: List[dict]) -> List[types.Content]:
        """Convert input message dicts to official Google GenAI Content types."""
        contents: List[types.Content] = []
        for msg in messages:
            role = msg.get("role", "user")
            # Map 'assistant' to 'model' for Gemini standard
            if role in {"assistant", "model"}:
                gemini_role = "model"
            else:
                gemini_role = "user"

            content_text = str(msg.get("content", "")).strip()
            if not content_text:
                continue

            contents.append(
                types.Content(
                    role=gemini_role,
                    parts=[types.Part.from_text(text=content_text)]
                )
            )

        if not contents:
            raise GeminiAPIException(
                message="No valid messages provided.",
                status_code=400,
                detail="Message array cannot be empty."
            )
        return contents

    def _get_config(self, custom_system_prompt: Optional[str] = None) -> types.GenerateContentConfig:
        instruction = custom_system_prompt or self.system_prompt
        return types.GenerateContentConfig(
            system_instruction=instruction,
            temperature=0.7,
            top_p=0.95,
        )

    def generate_reply(
        self,
        messages: List[dict],
        custom_system_prompt: Optional[str] = None,
    ) -> dict:
        """Non-streaming response from Gemma 4 via Gemini API."""
        client = self._get_client()
        contents = self._convert_messages(messages)
        gen_config = self._get_config(custom_system_prompt)

        try:
            response = client.models.generate_content(
                model=self.model_name,
                contents=contents,
                config=gen_config,
            )
            reply_text = response.text or ""
            return {
                "role": "model",
                "content": reply_text,
                "model": self.model_name,
            }
        except APIError as exc:
            log.error("Google Gemini API error: %s", exc)
            status_code = getattr(exc, "code", 500)
            if status_code == 429:
                raise GeminiAPIException(
                    message="Rate limit exceeded on Gemini API quota.",
                    status_code=429,
                    detail="Too many requests. Please wait a moment before trying again."
                ) from exc
            elif status_code in (401, 403):
                raise GeminiAPIException(
                    message="Invalid or unauthorized GEMINI_API_KEY.",
                    status_code=401,
                    detail=str(exc)
                ) from exc
            else:
                raise GeminiAPIException(
                    message=f"Gemini API request failed ({status_code})",
                    status_code=502,
                    detail=str(exc)
                ) from exc
        except Exception as exc:
            log.exception("Unexpected error communicating with Gemini API: %s", exc)
            raise GeminiAPIException(
                message="Internal model generation error.",
                status_code=500,
                detail=str(exc)
            ) from exc

    def stream_reply(
        self,
        messages: List[dict],
        custom_system_prompt: Optional[str] = None,
    ) -> Generator[str, None, None]:
        """Streaming response (chunks) from Gemma 4 via Gemini API."""
        client = self._get_client()
        contents = self._convert_messages(messages)
        gen_config = self._get_config(custom_system_prompt)

        try:
            stream = client.models.generate_content_stream(
                model=self.model_name,
                contents=contents,
                config=gen_config,
            )
            for chunk in stream:
                if chunk.text:
                    yield chunk.text
        except APIError as exc:
            log.error("Gemini API streaming error: %s", exc)
            status_code = getattr(exc, "code", 500)
            if status_code == 429:
                raise GeminiAPIException(
                    message="Rate limit exceeded on Gemini API quota.",
                    status_code=429,
                    detail="Quota limit reached."
                ) from exc
            else:
                raise GeminiAPIException(
                    message=f"Gemini streaming failed: {exc}",
                    status_code=502,
                    detail=str(exc)
                ) from exc
        except Exception as exc:
            log.exception("Unexpected streaming failure: %s", exc)
            raise GeminiAPIException(
                message="Stream processing error.",
                status_code=500,
                detail=str(exc)
            ) from exc


_singleton_service: Optional[GemmaChatService] = None

def get_chat_service() -> GemmaChatService:
    global _singleton_service
    if _singleton_service is None:
        _singleton_service = GemmaChatService()
    return _singleton_service
