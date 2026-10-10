"""FastAPI route handlers and rate limiting for /api/chat."""
from __future__ import annotations

import json
import logging
import time
from collections import defaultdict
from typing import List, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

from backend.chat.service import GeminiAPIException, GemmaChatService, get_chat_service

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["chat"])

# =========================================================================
# In-Memory IP Rate Limiter (Sliding Window: max 30 requests / 60 seconds)
# =========================================================================
RATE_LIMIT_MAX_REQUESTS = 30
RATE_LIMIT_WINDOW_SECONDS = 60
_ip_request_timestamps: dict[str, list[float]] = defaultdict(list)


def check_rate_limit(request: Request) -> None:
    """Enforce per-IP rate limiting."""
    client_ip = request.client.host if request.client else "unknown"
    now = time.time()
    cutoff = now - RATE_LIMIT_WINDOW_SECONDS

    # Clean old timestamps
    timestamps = [ts for ts in _ip_request_timestamps[client_ip] if ts > cutoff]
    if len(timestamps) >= RATE_LIMIT_MAX_REQUESTS:
        retry_after = int(RATE_LIMIT_WINDOW_SECONDS - (now - timestamps[0])) + 1
        log.warning("Rate limit exceeded for IP: %s", client_ip)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": "Rate limit exceeded",
                "message": f"Maximum {RATE_LIMIT_MAX_REQUESTS} requests per minute allowed.",
                "retry_after_seconds": max(1, retry_after),
            },
            headers={"Retry-After": str(max(1, retry_after))},
        )

    timestamps.append(now)
    _ip_request_timestamps[client_ip] = timestamps


# =========================================================================
# Request and Response Schemas
# =========================================================================
class ChatMessage(BaseModel):
    role: Literal["user", "model", "assistant"] = Field(
        ...,
        description="Sender role ('user' or 'model'/'assistant')",
    )
    content: str = Field(
        ...,
        min_length=1,
        max_length=4000,
        description="Text content of the message",
    )


class ChatRequest(BaseModel):
    messages: List[ChatMessage] = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Conversation history (max 50 messages)",
    )
    stream: bool = Field(
        default=False,
        description="Whether to stream response tokens via Server-Sent Events",
    )
    system_prompt: Optional[str] = Field(
        default=None,
        description="Optional request-specific system instruction override",
    )


class ChatResponse(BaseModel):
    role: str = "model"
    content: str
    model: str


# =========================================================================
# Endpoints
# =========================================================================
@router.post(
    "/chat",
    response_model=ChatResponse,
    summary="Chat with Google Gemma 4 via Gemini API",
    dependencies=[Depends(check_rate_limit)],
)
async def chat_endpoint(
    req: ChatRequest,
    chat_service: GemmaChatService = Depends(get_chat_service),
):
    """
    POST /api/chat
    Supports normal JSON reply and Server-Sent Events (SSE) streaming.
    """
    msg_dicts = [m.model_dump() for m in req.messages]

    # Streaming mode
    if req.stream:
        def sse_event_generator():
            try:
                for text_chunk in chat_service.stream_reply(
                    msg_dicts, custom_system_prompt=req.system_prompt
                ):
                    payload = json.dumps({"delta": text_chunk})
                    yield f"data: {payload}\n\n"
                yield "data: [DONE]\n\n"
            except GeminiAPIException as exc:
                err_payload = json.dumps({"error": exc.message, "detail": exc.detail})
                yield f"event: error\ndata: {err_payload}\n\n"
            except Exception as exc:
                err_payload = json.dumps({"error": "Streaming failed", "detail": str(exc)})
                yield f"event: error\ndata: {err_payload}\n\n"

        return StreamingResponse(
            sse_event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    # Standard JSON reply
    try:
        reply_data = chat_service.generate_reply(
            msg_dicts, custom_system_prompt=req.system_prompt
        )
        return ChatResponse(
            role=reply_data["role"],
            content=reply_data["content"],
            model=reply_data["model"],
        )
    except GeminiAPIException as exc:
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": exc.message, "detail": exc.detail},
        )
    except Exception as exc:
        log.exception("Unexpected error in /api/chat: %s", exc)
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error", "detail": str(exc)},
        )
