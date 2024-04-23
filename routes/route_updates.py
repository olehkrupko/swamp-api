from flask import request, Blueprint

import routes._shared as shared
from models.model_updates import Update


router = Blueprint("updates", __name__, url_prefix="/updates")


@router.route("/", methods=["GET"])
@cross_origin(headers=["Content-Type"])  # Send Access-Control-Allow-Headers
def list_updates():
    kwargs = dict(request.args)

    updates = Update.get_updates(**kwargs)

    return shared.return_json(
        response=updates,
    )
