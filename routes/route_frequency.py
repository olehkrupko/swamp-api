from fastapi import APIRouter

from responses.PrettyJsonResponse import PrettyJsonResponse
from services.service_frequency import Frequency


router = APIRouter(
    prefix="/frequency",
)


@router.get("/", response_class=PrettyJsonResponse)
def list_frequencies():
    return Frequency.list()
