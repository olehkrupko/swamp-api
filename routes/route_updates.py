"""Update retrieval and parsing routes.

Provides endpoints for listing updates and parsing updates from feed URLs.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from services.service_sqlalchemy import SQLAlchemy
from models.model_updates import Update
from responses.PrettyJsonResponse import PrettyJsonResponse


router = APIRouter(
    prefix="/updates",
)


@router.get("/", response_class=PrettyJsonResponse)
async def list_updates(
    limit: int = 300,
    private: bool | None = None,
    # TODO: separate _id to its own endpoint  /feed/{feed_id}/updates ?
    _id: int | None = None,
    session: AsyncSession = Depends(SQLAlchemy.get_db_session),
) -> list[dict[str, object]]:
    """List updates with optional filtering.

    Args:
        limit: Maximum number of updates to return (default 300).
        private: Filter by feed privacy (None = all).
        _id: Filter by specific feed ID (None = all).
        session: SQLAlchemy async session.

    Returns:
        list: List of update dicts enriched with feed data.
    """
    return await Update.get_updates(
        limit=limit,
        private=private,
        _id=_id,
        session=session,
    )


@router.get("/parse/", response_class=PrettyJsonResponse)
async def parse_updates(
    href: str,
) -> list[dict[str, object]]:
    """Parse updates from a feed URL.

    Args:
        href: Feed URL to parse.

    Returns:
        list: List of update dicts.

    Raises:
        HTTPException: 422 if swamp-parser fails.
    """
    return await Update.parse_href(href)
    # TODO: return 422 if swamp-parser fails
