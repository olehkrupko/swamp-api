from os import getenv

from fastapi import APIRouter

from models.model_updates import Update
from responses.PrettyJsonResponse import PrettyJsonResponse


router = APIRouter(
    prefix="/updates",
)


@router.get("/", response_class=PrettyJsonResponse)
async def list_updates(
    **body: dict,
):
    return await Update.get_updates(**body)


@router.get("/parse/", response_class=PrettyJsonResponse)
async def parse_updates(
    href: str,
):
    return Update.parse_href(href)
