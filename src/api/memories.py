"""Memory browsing API endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
import structlog

from src.api.dependencies import get_current_user
from src.database import get_pool
from src.models.user import User

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/memories", tags=["Memories"])


@router.get("")
async def list_memories(
    q: str | None = Query(default=None, description="Search query"),
    type: str | None = Query(default=None, description="Filter by memory type"),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
) -> dict:
    """List or search user's memories with optional filters."""
    user_id = str(current_user.id)
    pool = await get_pool()

    # Build query dynamically
    conditions = ["user_id = $1", "deleted_at IS NULL", "status = 'active'"]
    params: list = [user_id]
    param_idx = 2

    if type:
        conditions.append(f"type = ${param_idx}")
        params.append(type)
        param_idx += 1

    if q:
        conditions.append(f"content ILIKE ${param_idx}")
        params.append(f"%{q}%")
        param_idx += 1

    where_clause = " AND ".join(conditions)

    async with pool.acquire() as conn:
        total = await conn.fetchval(
            f"SELECT COUNT(*) FROM memory_items WHERE {where_clause}",
            *params,
        )

        rows = await conn.fetch(
            f"""
            SELECT id, content, type, importance, confidence,
                   source_conversation_id, created_at
            FROM memory_items
            WHERE {where_clause}
            ORDER BY created_at DESC
            LIMIT ${param_idx} OFFSET ${param_idx + 1}
            """,
            *params,
            limit,
            offset,
        )

    items = [
        {
            "id": str(row["id"]),
            "content": row["content"],
            "type": row["type"],
            "importance": float(row["importance"]),
            "confidence": float(row["confidence"]),
            "source_conversation_id": str(row["source_conversation_id"]) if row["source_conversation_id"] else None,
            "created_at": row["created_at"].isoformat(),
        }
        for row in rows
    ]

    return {
        "items": items,
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.delete("/{memory_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_memory(
    memory_id: UUID,
    current_user: User = Depends(get_current_user),
) -> None:
    """Soft-delete a memory item (user-scoped)."""
    user_id = str(current_user.id)
    pool = await get_pool()

    async with pool.acquire() as conn:
        result = await conn.execute(
            """
            UPDATE memory_items
            SET deleted_at = NOW(), status = 'deleted'
            WHERE id = $1 AND user_id = $2 AND deleted_at IS NULL
            """,
            memory_id,
            user_id,
        )

    if result != "UPDATE 1":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Memory not found",
        )

    logger.info("memory_deleted", memory_id=str(memory_id), user_id=user_id)
