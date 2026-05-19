"""Frequency lookup routes.

Provides an endpoint to return available feed frequency values.
"""

from fastapi import APIRouter

from responses.PrettyJsonResponse import PrettyJsonResponse
from services.service_frequency import Frequency


router = APIRouter(
    prefix="/frequency",
)


@router.get("/", response_class=PrettyJsonResponse)
def list_frequencies() -> list:
    """Return configured feed frequency options.
    
    Returns:
        list: Available frequency values supported by the API.
    """
    return Frequency.list()
