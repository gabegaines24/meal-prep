"""
SSE chat endpoint for the meal planning copilot.
"""

import json
from typing import Any, Optional

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models.models import ChatHistory
from backend.services import agent as agent_svc

router = APIRouter()

HISTORY_LIMIT = 40
MEMORY_CONDENSE_EVERY = 10


class ChatContext(BaseModel):
    scan_ingredients: Optional[list[str]] = None


class ChatRequest(BaseModel):
    session_id: str
    message: str
    context: Optional[ChatContext] = None


def _load_history(db: Session, session_id: str) -> list[dict]:
    rows = (
        db.query(ChatHistory)
        .filter(ChatHistory.session_id == session_id)
        .order_by(ChatHistory.created_at.asc())
        .limit(HISTORY_LIMIT)
        .all()
    )
    messages: list[dict] = []
    for row in rows:
        if row.role == "tool":
            continue
        messages.append({"role": row.role, "content": row.content})
    return messages


def _save_message(db: Session, session_id: str, role: str, content: str) -> None:
    db.add(ChatHistory(session_id=session_id, role=role, content=content))
    db.commit()


def _user_turn_count(db: Session, session_id: str) -> int:
    return (
        db.query(ChatHistory)
        .filter(ChatHistory.session_id == session_id, ChatHistory.role == "user")
        .count()
    )


def _sse(event: dict) -> str:
    return f"data: {json.dumps(event, default=str)}\n\n"


@router.post("")
async def chat(request: ChatRequest, db: Session = Depends(get_db)):
    """Stream agent responses as Server-Sent Events."""
    scan_ingredients = (
        request.context.scan_ingredients if request.context else None
    )

    history = _load_history(db, request.session_id)
    history.append({"role": "user", "content": request.message})
    _save_message(db, request.session_id, "user", request.message)

    rag_context = agent_svc.build_rag_context(request.message, scan_ingredients)

    async def event_stream():
        assistant_text = ""
        try:
            async for event in agent_svc.run_agent(db, history, rag_context):
                if event.get("type") == "token":
                    assistant_text += event.get("content", "")
                yield _sse(event)

                if event.get("type") in ("action", "citation"):
                    pass  # forwarded to client as-is

            if assistant_text.strip():
                _save_message(db, request.session_id, "assistant", assistant_text.strip())

            turn_count = _user_turn_count(db, request.session_id)
            if turn_count > 0 and turn_count % MEMORY_CONDENSE_EVERY == 0:
                all_msgs = _load_history(db, request.session_id)
                summary = await agent_svc.condense_memory(request.session_id, all_msgs)
                if summary:
                    yield _sse({"type": "memory", "summary": summary})

        except Exception as exc:
            yield _sse({"type": "error", "content": str(exc)})
            yield _sse({"type": "done"})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/history/{session_id}")
def get_history(session_id: str, db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    rows = (
        db.query(ChatHistory)
        .filter(
            ChatHistory.session_id == session_id,
            ChatHistory.role.in_(["user", "assistant"]),
        )
        .order_by(ChatHistory.created_at.asc())
        .limit(HISTORY_LIMIT)
        .all()
    )
    return [
        {"role": row.role, "content": row.content, "created_at": row.created_at.isoformat()}
        for row in rows
    ]
