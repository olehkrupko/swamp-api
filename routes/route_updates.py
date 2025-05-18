from fastapi import APIRouter

from models.model_updates import Update
from responses.PrettyJsonResponse import PrettyJsonResponse


router = APIRouter(
    prefix="/updates",
)


@router.get("/", response_class=PrettyJsonResponse)
async def list_updates(
    limit: int = 300,
    private: bool = None,
    # TODO: separate _id to its own endpoint  /feed/{feed_id}/updates ?
    _id: int = None,
):
    return await Update.get_updates(
        limit=limit,
        private=private,
        _id=_id,
    )


@router.get("/parse/", response_class=PrettyJsonResponse)
async def parse_updates(
    href: str,
):
    return await Update.parse_href(href)
