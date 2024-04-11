from flask import Blueprint

import routes._shared as shared
from services.service_frequency import Frequency


router = Blueprint("frequency", __name__, url_prefix="/frequency")


@router.route("/", methods=["GET"])
def list_frequencies():
    return shared.return_json(
        response=Frequency.list(),
    )
