from flask import Blueprint

import routes._shared as shared
from services.service_frequencies import Frequencies


router = Blueprint("frequencies", __name__, url_prefix="/frequencies")


@router.route("/", methods=["GET"])
def feeds_frequencies():
    return shared.return_json(
        response=Frequencies.get_options(),
    )
