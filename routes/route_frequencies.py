from flask import Blueprint

import routes._shared as shared
from models.model_frequencies import FREQUENCIES


router = Blueprint("frequencies", __name__, url_prefix="/frequencies")


@router.route("/", methods=["GET"])
def feeds_frequencies():
    return shared.return_json(
        response=FREQUENCIES,
    )
